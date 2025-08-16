import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meals_system.settings')
django.setup()

from meals.models import Student, ClassRoom, StudentPayment, MealRecord
from decimal import Decimal
from datetime import datetime, timedelta

def test_import_logic():
    print("=== TEST LOGIC IMPORT PAYMENT ===")
    
    # Tìm lớp và học sinh
    classroom = ClassRoom.objects.filter(name='CAT HÈ 2025', term='Hè 2025').first()
    student = Student.objects.filter(classroom=classroom, name__icontains='Lâm Uyển Như').first()
    
    print(f"Lớp: {classroom}")
    print(f"Học sinh: {student}")
    
    # Giả lập quá trình import tháng 8
    month = "2025-08"
    amount = Decimal("1500000")  # 1,500,000₫
    term = "Hè 2025"
    classroom_id = classroom.id
    
    print(f"\n🔍 GIẢ LẬP IMPORT THÁNG {month}:")
    print(f"💰 Số tiền import: {amount:,.0f}₫")
    
    # 1) Xác định meal_price_id và tuition_fee trước
    prior = (StudentPayment.objects
            .filter(student=student)
            .exclude(month=month)
            .order_by('-month')
            .first())
    
    if prior:
        price_id, fee = prior.meal_price_id, prior.tuition_fee
        print(f"✅ Lấy từ tháng trước: meal_price_id={price_id}, tuition_fee={fee:,.0f}₫")
    else:
        price_id, fee = 2, 0
        print(f"⚠️ Không có tháng trước, dùng mặc định: meal_price_id={price_id}, tuition_fee={fee:,.0f}₫")
    
    # 2) Tạo mới hoặc update
    sp, created = StudentPayment.objects.get_or_create(
        student=student,
        month=month,
        defaults={
            'amount_paid':     amount,
            'meal_price_id':   price_id,
            'tuition_fee':     fee,
        }
    )
    
    if created:
        print(f"✅ Tạo mới StudentPayment: ID={sp.id}")
    else:
        print(f"🔄 Cập nhật StudentPayment hiện có: ID={sp.id}")
        sp.amount_paid     = amount
        sp.meal_price_id   = price_id
        sp.tuition_fee     = fee
    
    print(f"📊 Trước khi save():")
    print(f"   amount_paid: {sp.amount_paid:,.0f}₫")
    print(f"   tuition_fee: {sp.tuition_fee:,.0f}₫")
    print(f"   meal_price_id: {sp.meal_price_id}")
    print(f"   remaining_balance: {sp.remaining_balance:,.0f}₫" if sp.remaining_balance else "   remaining_balance: None")
    
    # 3) Lưu - đây là bước quan trọng!
    print(f"\n💾 Đang gọi sp.save()...")
    sp.save()
    
    print(f"📊 Sau khi save():")
    print(f"   amount_paid: {sp.amount_paid:,.0f}₫")
    print(f"   tuition_fee: {sp.tuition_fee:,.0f}₫")
    print(f"   meal_price_id: {sp.meal_price_id}")
    print(f"   remaining_balance: {sp.remaining_balance:,.0f}₫")
    
    # Kiểm tra lại từ database
    sp.refresh_from_db()
    print(f"\n🔄 Sau khi refresh_from_db():")
    print(f"   amount_paid: {sp.amount_paid:,.0f}₫")
    print(f"   tuition_fee: {sp.tuition_fee:,.0f}₫")
    print(f"   meal_price_id: {sp.meal_price_id}")
    print(f"   remaining_balance: {sp.remaining_balance:,.0f}₫")
    
    # Kiểm tra logic tính toán
    print(f"\n🔢 KIỂM TRA LOGIC TÍNH TOÁN:")
    
    # Tìm prior_remain_balance
    dt = datetime.strptime(month, '%Y-%m')
    prev_month = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    prev_payment = StudentPayment.objects.filter(student=student, month=prev_month).order_by('-id').first()
    
    if prev_payment:
        prior_balance = prev_payment.remaining_balance
        print(f"   prior_remain_balance: {prior_balance:,.0f}₫ (từ tháng {prev_month})")
    else:
        # Tìm tháng gần nhất có dữ liệu
        prior = StudentPayment.objects.filter(student=student).exclude(month=month).order_by('-month').first()
        if prior:
            prior_balance = prior.remaining_balance
            print(f"   prior_remain_balance: {prior_balance:,.0f}₫ (từ tháng {prior.month})")
        else:
            prior_balance = 0
            print(f"   prior_remain_balance: 0₫ (không có tháng trước)")
    
    # Tính tổng tiền ăn
    year, month_int = month.split('-')
    meal_records = MealRecord.objects.filter(
        student=student,
        date__year=int(year),
        date__month=int(month_int)
    ).order_by('date', 'meal_type')
    
    total_meal_charge = 0
    for record in meal_records:
        if record.meal_type == "Bữa sáng":
            if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                total_meal_charge += sp.meal_price.breakfast_price
        elif record.meal_type == "Bữa trưa":
            if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                total_meal_charge += sp.meal_price.lunch_price
    
    print(f"   total_meal_charge: {total_meal_charge:,}₫")
    
    # Tính toán expected
    expected_balance = sp.amount_paid - sp.tuition_fee - Decimal(total_meal_charge) + prior_balance
    print(f"\n   Công thức: {sp.amount_paid:,.0f} - {sp.tuition_fee:,.0f} - {total_meal_charge:,} + {prior_balance:,.0f}")
    print(f"   Kết quả: {expected_balance:,.0f}₫")
    
    if sp.remaining_balance != expected_balance:
        print(f"   ⚠️ SỐ DƯ KHÔNG KHỚP!")
        print(f"      Tính toán: {expected_balance:,.0f}₫")
        print(f"      Thực tế: {sp.remaining_balance:,.0f}₫")
        print(f"      Chênh lệch: {abs(expected_balance - sp.remaining_balance):,.0f}₫")
    else:
        print(f"   ✅ Số dư tính đúng: {sp.remaining_balance:,.0f}₫")

if __name__ == "__main__":
    test_import_logic()

