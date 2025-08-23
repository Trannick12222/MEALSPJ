from .models import MealPrice

def get_current_price() -> MealPrice:
    """
    Trả về bản MealPrice mới nhất (effective_date lớn nhất).
    """
    return MealPrice.objects.first()

def get_sorted_terms():
    """
    Lấy danh sách term được sắp xếp theo logic năm học thực tế
    Thay vì sắp xếp theo thứ tự từ điển
    """
    from .models import ClassRoom
    
    # Lấy tất cả terms
    all_terms = ClassRoom.objects.values_list('term', flat=True).distinct()
    
    def extract_year(term):
        """Trích xuất năm từ term để sắp xếp"""
        if term == 'Nghỉ/Nghỉ Giữa Chừng':
            return 0  # Đặt ở cuối cùng
        
        # Tìm số năm trong term
        import re
        years = re.findall(r'\d{4}', term)
        if years:
            return int(years[-1])  # Lấy năm cuối cùng
        
        # Nếu không tìm thấy năm, thử tìm năm 2 chữ số
        years = re.findall(r'\d{2}', term)
        if years:
            year = int(years[-1])
            # Giả sử năm 2 chữ số là 20xx
            return 2000 + year
        
        return 0  # Mặc định
    
    # Sắp xếp theo năm học (mới nhất trước) và loại bỏ trùng lặp
    sorted_terms = sorted(all_terms, key=extract_year, reverse=True)
    
    # Loại trừ "Nghỉ/Nghỉ Giữa Chừng" và lấy 2 term gần nhất, loại bỏ trùng lặp
    filtered_terms = []
    seen_terms = set()
    for term in sorted_terms:
        if term != 'Nghỉ/Nghỉ Giữa Chừng' and term not in seen_terms:
            filtered_terms.append(term)
            seen_terms.add(term)
            if len(filtered_terms) >= 2:
                break
    
    return filtered_terms


def can_edit_term_data(term, current_date=None):
    """
    Kiểm tra xem có thể chỉnh sửa dữ liệu của term này không
    dựa trên nguyên tắc: chỉ cho phép chỉnh sửa tháng trước đó
    
    Args:
        term: Tên term cần kiểm tra
        current_date: Ngày hiện tại (mặc định là today)
    
    Returns:
        dict: {
            'can_edit': bool,
            'reason': str,
            'allowed_months': list,  # Danh sách tháng được phép chỉnh sửa
            'current_month': int,
            'current_year': int
        }
    """
    from datetime import date, datetime
    from .models import MealRecord, ClassRoom
    
    if current_date is None:
        current_date = date.today()
    
    current_month = current_date.month
    current_year = current_date.year
    
    # Lấy danh sách term được sắp xếp
    sorted_terms = get_sorted_terms()
    
    if not sorted_terms:
        return {
            'can_edit': False,
            'reason': 'Không có term nào trong hệ thống',
            'allowed_months': [],
            'current_month': current_month,
            'current_year': current_year
        }
    
    # Tìm vị trí của term trong danh sách
    try:
        term_index = sorted_terms.index(term)
    except ValueError:
        return {
            'can_edit': False,
            'reason': f'Term "{term}" không tồn tại trong danh sách hiện tại',
            'allowed_months': [],
            'current_month': current_month,
            'current_year': current_year
        }
    
    # Term hiện tại (mới nhất)
    current_term = sorted_terms[0]
    
    # Nếu đây là term hiện tại
    if term == current_term:
        # Term hiện tại có thể chỉnh sửa dữ liệu ở MỌI THÁNG
        return {
            'can_edit': True,
            'reason': f'Term hiện tại: có thể thêm và chỉnh sửa dữ liệu ở mọi tháng',
            'allowed_months': ['all'],  # Đặc biệt: 'all' có nghĩa là mọi tháng
            'current_month': current_month,
            'current_year': current_year
        }
    
    # Nếu đây là term trước đó
    elif term_index == 1:  # Term thứ 2 trong danh sách
        # Kiểm tra xem term hiện tại có dữ liệu ở tháng hiện tại không
        current_term_has_data = MealRecord.objects.filter(
            student__classroom__term=current_term,
            date__year=current_year,
            date__month=current_month
        ).exists()
        
        # Nếu term hiện tại chưa có dữ liệu
        if not current_term_has_data:
            # Cho phép chỉnh sửa tháng hiện tại và tháng trước của term trước
            allowed_months = []
            
            # Tháng hiện tại
            allowed_months.append(f"{current_month}/{current_year}")
            
            # Tháng trước
            prev_month = current_month - 1
            prev_year = current_year
            if prev_month == 0:
                prev_month = 12
                prev_year = current_year - 1
            allowed_months.append(f"{prev_month}/{prev_year}")
            
            # Kiểm tra xem term trước có dữ liệu trong các tháng được phép không
            has_data = False
            for month_str in allowed_months:
                month, year = map(int, month_str.split('/'))
                if MealRecord.objects.filter(
                    student__classroom__term=term,
                    date__year=year,
                    date__month=month
                ).exists():
                    has_data = True
                    break
            
            if has_data:
                return {
                    'can_edit': True,
                    'reason': f'Term hiện tại chưa có dữ liệu, có thể chỉnh sửa tháng {", ".join(allowed_months)} của term trước',
                    'allowed_months': allowed_months,
                    'current_month': current_month,
                    'current_year': current_year
                }
            else:
                return {
                    'can_edit': False,
                    'reason': f'Term trước không có dữ liệu trong tháng {", ".join(allowed_months)}',
                    'allowed_months': [],
                    'current_month': current_month,
                    'current_year': current_year
                }
        else:
            # Term hiện tại đã có dữ liệu, chỉ cho phép chỉnh sửa tháng trước
            allowed_month = current_month - 1
            allowed_year = current_year
            if allowed_month == 0:
                allowed_month = 12
                allowed_year = current_year - 1
            
            # Kiểm tra xem term trước có dữ liệu trong tháng được phép không
            has_data = MealRecord.objects.filter(
                student__classroom__term=term,
                date__year=allowed_year,
                date__month=allowed_month
            ).exists()
            
            if has_data:
                return {
                    'can_edit': True,
                    'reason': f'Term hiện tại đã có dữ liệu, chỉ có thể chỉnh sửa tháng {allowed_month}/{allowed_year} của term trước',
                    'allowed_months': [f"{allowed_month}/{allowed_year}"],
                    'current_month': current_month,
                    'current_year': current_year
                }
            else:
                return {
                    'can_edit': False,
                    'reason': f'Term trước không có dữ liệu trong tháng {allowed_month}/{allowed_year}',
                    'allowed_months': [],
                    'current_month': current_month,
                    'current_year': current_year
                }
    
    # Các term cũ hơn
    else:
        return {
            'can_edit': False,
            'reason': f'Term "{term}" quá cũ, không được phép chỉnh sửa',
            'allowed_months': [],
            'current_month': current_month,
            'current_year': current_year
        }


def can_edit_specific_date(term, target_date, current_date=None):
    """
    Kiểm tra xem có thể chỉnh sửa dữ liệu của một ngày cụ thể không
    
    Args:
        term: Tên term
        target_date: Ngày muốn chỉnh sửa
        current_date: Ngày hiện tại
    
    Returns:
        bool: True nếu có thể chỉnh sửa
    """
    if current_date is None:
        from datetime import date
        current_date = date.today()
    
    # Lấy thông tin quyền chỉnh sửa
    edit_info = can_edit_term_data(term, current_date)
    
    if not edit_info['can_edit']:
        return False
    
    # Nếu là term hiện tại (có quyền 'all')
    if edit_info['allowed_months'] == ['all']:
        return True
    
    # Kiểm tra xem target_date có trong tháng được phép không
    target_month = target_date.month
    target_year = target_date.year
    
    for allowed_month_str in edit_info['allowed_months']:
        month, year = map(int, allowed_month_str.split('/'))
        if target_month == month and target_year == year:
            return True
    
    return False


def get_editable_terms_info(current_date=None):
    """
    Lấy thông tin về các term có thể chỉnh sửa
    
    Returns:
        dict: {
            'current_term': str,
            'editable_terms': [
                {
                    'term': str,
                    'can_edit': bool,
                    'reason': str,
                    'allowed_months': list
                }
            ]
        }
    """
    from datetime import date
    
    if current_date is None:
        current_date = date.today()
    
    sorted_terms = get_sorted_terms()
    
    if not sorted_terms:
        return {
            'current_term': None,
            'editable_terms': []
        }
    
    current_term = sorted_terms[0]
    editable_terms = []
    
    for term in sorted_terms:
        edit_info = can_edit_term_data(term, current_date)
        editable_terms.append({
            'term': term,
            'can_edit': edit_info['can_edit'],
            'reason': edit_info['reason'],
            'allowed_months': edit_info['allowed_months']
        })
    
    return {
        'current_term': current_term,
        'editable_terms': editable_terms
    }
