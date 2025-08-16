import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meals_system.settings')
django.setup()

from meals.models import Student, ClassRoom, StudentPayment, MealRecord
from decimal import Decimal
from datetime import datetime, timedelta

def debug_save_method():
    print("=== DEBUG STUDENTPAYMENT.SAVE() METHOD ===")
    
    # Tìm lớp và học sinh
    classroom = ClassRoom.objects.filter(name='CAT HÈ 2025', term='Hè 2025').first()
    student = Student.objects.filter(classroom=classroom, name__icontains='Lâm Uyển Như').first()
    
    print(f"Lớp: {classroom}")
    print(f"Học sinh: {student}")
    
    # Tìm payment tháng 8
    payment = StudentPayment.objects.filter(student=student, month='2025-08').first()
    if not payment:
        print("❌ Không tìm thấy payment tháng 8")
        return
    
    print(f"\n📅 PAYMENT THÁNG 8: ID={payment.id}")
    print(f"💰 amount_paid: {payment.amount_paid:,.0f}₫")
    print(f"🏫 tuition_fee: {payment.tuition_fee:,.0f}₫")
    print(f"🍽️ meal_price: {payment.meal_price.daily_price:,}₫/ngày")
    print(f"💳 remaining_balance: {payment.remaining_balance:,.0f}₫")
    
    # Giả lập logic trong save() method
    print(f"\n🔍 GIẢ LẬP LOGIC TRONG SAVE() METHOD:")
    
    # 1. Tính prior_remain_balance
    month = "2025-08"
    prior_remain_balance = 0
    if month:
        dt = datetime.strptime(month, '%Y-%m')
        prev_month = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        print(f"   Tháng hiện tại: {month}")
        print(f"   Tháng trước (theo logic): {prev_month}")
        
        prev_payment = StudentPayment.objects.filter(student=student, month=prev_month).order_by('-id').first()
        if prev_payment and prev_payment.remaining_balance:
            prior_remain_balance = prev_payment.remaining_balance
            print(f"   ✅ Tìm thấy payment tháng trước: {prev_month}")
            print(f"   💰 prior_remain_balance: {prior_remain_balance:,.0f}₫")
        else:
            print(f"   ❌ Không tìm thấy payment tháng trước: {prev_month}")
            print(f"   💰 prior_remain_balance: 0₫")
    
    # 2. Tính total_meal_charge
    try:
        year_str, month_str = month.split("-")
        year = int(year_str)
        month_int = int(month_str)
        print(f"   Năm: {year}, Tháng: {month_int}")
    except Exception as e:
        print(f"   ❌ Lỗi parse tháng: {e}")
        year = None
        month_int = None
    
    total_meal_charge = 0
    if year and month_int:
        meal_records = student.mealrecord_set.filter(
            date__year=year, 
            date__month=month_int, 
            meal_type__in=["Bữa sáng", "Bữa trưa"]
        )
        print(f"   📝 Số bữa ăn tìm thấy: {meal_records.count()}")
        
        # Lấy giá
        fee_breakfast = payment.meal_price.breakfast_price
        fee_lunch = payment.meal_price.lunch_price
        print(f"   🍳 Giá bữa sáng: {fee_breakfast:,}₫")
        print(f"   🍽️ Giá bữa trưa: {fee_lunch:,}₫")
        
        # Tính tiền từng bữa
        for record in meal_records:
            if record.meal_type == "Bữa sáng":
                if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                    total_meal_charge += fee_breakfast
                    print(f"      🍳 {record.date}: Bữa sáng - {record.status} (non_eat={record.non_eat}) → +{fee_breakfast:,}₫")
                else:
                    print(f"      🍳 {record.date}: Bữa sáng - {record.status} (non_eat={record.non_eat}) → +0₫")
            elif record.meal_type == "Bữa trưa":
                if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                    total_meal_charge += fee_lunch
                    print(f"      🍽️ {record.date}: Bữa trưa - {record.status} (non_eat={record.non_eat}) → +{fee_lunch:,}₫")
                else:
                    print(f"      🍽️ {record.date}: Bữa trưa - {record.status} (non_eat={record.non_eat}) → +0₫")
    else:
        print(f"   ❌ Không thể tính total_meal_charge")
    
    print(f"   💵 Tổng tiền ăn: {total_meal_charge:,}₫")
    
    # 3. Tính remaining_balance
    expected_balance = payment.amount_paid - payment.tuition_fee - Decimal(total_meal_charge) + prior_remain_balance
    print(f"\n🔢 TÍNH TOÁN REMAINING_BALANCE:")
    print(f"   Công thức: {payment.amount_paid:,.0f} - {payment.tuition_fee:,.0f} - {total_meal_charge:,} + {prior_remain_balance:,.0f}")
    print(f"   Kết quả: {expected_balance:,.0f}₫")
    
    # 4. So sánh với giá trị thực tế
    actual_balance = payment.remaining_balance
    print(f"\n📊 SO SÁNH:")
    print(f"   Tính toán: {expected_balance:,.0f}₫")
    print(f"   Thực tế: {actual_balance:,.0f}₫")
    
    if expected_balance != actual_balance:
        print(f"   ⚠️ KHÔNG KHỚP!")
        print(f"   Chênh lệch: {abs(expected_balance - actual_balance):,.0f}₫")
        
        # Kiểm tra vấn đề
        print(f"\n🔍 PHÂN TÍCH VẤN ĐỀ:")
        
        # Kiểm tra xem có phải vấn đề với prior_remain_balance không
        if prior_remain_balance == 0:
            print(f"   ❌ VẤN ĐỀ: prior_remain_balance = 0")
            print(f"   Tháng 7 không có payment, nhưng tháng 6 có remaining_balance = -2,000,000₫")
            print(f"   Logic tìm tháng trước có vấn đề!")
        else:
            print(f"   ✅ prior_remain_balance đúng: {prior_remain_balance:,.0f}₫")
        
        # Kiểm tra meal_price
        if not payment.meal_price:
            print(f"   ❌ VẤN ĐỀ: meal_price = None")
        else:
            print(f"   ✅ meal_price đúng: {payment.meal_price.daily_price:,}₫/ngày")
        
        # Kiểm tra meal_records
        if meal_records.count() == 0:
            print(f"   ❌ VẤN ĐỀ: Không có meal records")
        else:
            print(f"   ✅ meal_records đúng: {meal_records.count()} bữa")
    else:
        print(f"   ✅ KHỚP!")
    
    # 5. Kiểm tra logic tìm tháng trước
    print(f"\n🔍 KIỂM TRA LOGIC TÌM THÁNG TRƯỚC:")
    print(f"   Tháng hiện tại: {month}")
    
    # Logic hiện tại (có vấn đề)
    dt = datetime.strptime(month, '%Y-%m')
    prev_month_broken = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    print(f"   Logic hiện tại: {month} → {prev_month_broken}")
    
    # Logic đúng (tìm tháng gần nhất có dữ liệu)
    all_payments = StudentPayment.objects.filter(student=student).exclude(month=month).order_by('-month')
    if all_payments.exists():
        correct_prior_month = all_payments.first().month
        correct_prior_balance = all_payments.first().remaining_balance
        print(f"   Logic đúng: {month} → {correct_prior_month} (remaining_balance: {correct_prior_balance:,.0f}₫)")
        
        if prev_month_broken != correct_prior_month:
            print(f"   ⚠️ LOGIC TÌM THÁNG TRƯỚC SAI!")
            print(f"      Logic hiện tại tìm: {prev_month_broken}")
            print(f"      Logic đúng phải tìm: {correct_prior_month}")
        else:
            print(f"   ✅ Logic tìm tháng trước đúng")
    else:
        print(f"   ❌ Không có payment nào khác")

if __name__ == "__main__":
    debug_save_method()

