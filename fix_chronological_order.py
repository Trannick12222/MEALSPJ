import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meals_system.settings')
django.setup()

from meals.models import Student, ClassRoom, StudentPayment, MealRecord
from decimal import Decimal
from datetime import datetime, timedelta

def fix_chronological_order():
    print("=== FIX THỨ TỰ TÍNH TOÁN THEO THỨ TỰ THÁNG ===")
    
    # Tìm lớp và học sinh
    classroom = ClassRoom.objects.filter(name='CAT HÈ 2025', term='Hè 2025').first()
    if not classroom:
        print("❌ Không tìm thấy lớp CAT HÈ 2025")
        return
        
    student = Student.objects.filter(classroom=classroom, name__icontains='Lâm Uyển Như').first()
    if not student:
        print("❌ Không tìm thấy học sinh Lâm Uyển Như")
        return
    
    print(f"🏫 Lớp: {classroom}")
    print(f"👤 Học sinh: {student}")
    
    # Lấy tất cả payments theo thứ tự tháng (tháng 6 trước, tháng 8 sau)
    payments = StudentPayment.objects.filter(student=student).order_by('month')
    print(f"\n📋 PAYMENTS TRƯỚC KHI FIX:")
    
    for p in payments:
        print(f"   📅 Tháng {p.month}: Số dư {p.remaining_balance:,.0f}₫")
    
    # Fix từng tháng theo thứ tự thời gian
    print(f"\n🔄 FIX TỪNG THÁNG THEO THỨ TỰ THỜI GIAN:")
    
    for i, payment in enumerate(payments):
        print(f"\n   📊 Tháng {payment.month}:")
        
        # 1. Tính prior_remain_balance
        if i == 0:
            prior_remain_balance = 0
            print(f"      🆕 Tháng đầu tiên → prior_remain_balance = 0₫")
        else:
            # Logic mới: Tìm tháng gần nhất có dữ liệu (theo thứ tự thời gian)
            prior_payments = StudentPayment.objects.filter(student=student, month__lt=payment.month).order_by('-month')
            if prior_payments.exists():
                prior_payment = prior_payments.first()
                prior_remain_balance = prior_payment.remaining_balance
                print(f"      🔍 Logic mới: Tìm thấy tháng trước: {prior_payment.month}")
                print(f"      💰 prior_remain_balance: {prior_remain_balance:,.0f}₫")
            else:
                prior_remain_balance = 0
                print(f"      ❌ Không có tháng trước")
        
        # 2. Tính toán total_meal_charge
        try:
            year_str, month_str = payment.month.split("-")
            year = int(year_str)
            month = int(month_str)
            
            meal_records = student.mealrecord_set.filter(date__year=year, date__month=month, meal_type__in=["Bữa sáng", "Bữa trưa"])
            
            total_meal_charge = 0
            for record in meal_records:
                if record.meal_type == "Bữa sáng":
                    if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                        total_meal_charge += payment.meal_price.breakfast_price
                elif record.meal_type == "Bữa trưa":
                    if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                        total_meal_charge += payment.meal_price.lunch_price
            
            print(f"      🍽️ Tổng tiền ăn: {total_meal_charge:,.0f}₫")
            
        except Exception as e:
            print(f"      ❌ Lỗi tính tiền ăn: {e}")
            total_meal_charge = 0
        
        # 3. Tính toán expected balance
        expected_balance = payment.amount_paid - payment.tuition_fee - Decimal(total_meal_charge) + prior_remain_balance
        print(f"      🔢 Expected balance: {payment.amount_paid:,.0f} - {payment.tuition_fee:,.0f} - {total_meal_charge:,.0f} + {prior_remain_balance:,.0f} = {expected_balance:,.0f}₫")
        
        # 4. Cập nhật remaining_balance
        old_balance = payment.remaining_balance
        payment.remaining_balance = expected_balance
        payment.save()
        
        print(f"      💳 Cập nhật: {old_balance:,.0f}₫ → {expected_balance:,.0f}₫")
    
    # Kiểm tra kết quả sau khi fix
    print(f"\n📊 KẾT QUẢ SAU KHI FIX:")
    payments = StudentPayment.objects.filter(student=student).order_by('month')
    
    for p in payments:
        print(f"   📅 Tháng {p.month}: Số dư {p.remaining_balance:,.0f}₫")
    
    print(f"\n🎉 HOÀN THÀNH FIX THỨ TỰ!")

if __name__ == "__main__":
    fix_chronological_order()
