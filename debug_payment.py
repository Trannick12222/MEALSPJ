import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meals_system.settings')
django.setup()

from meals.models import Student, ClassRoom, StudentPayment, MealRecord
from decimal import Decimal

def debug_payment():
    print("=== DEBUG PAYMENT HỌC SINH LÂM UYỂN NHƯ ===")
    
    # Tìm lớp và học sinh
    classroom = ClassRoom.objects.filter(name='CAT HÈ 2025', term='Hè 2025').first()
    student = Student.objects.filter(classroom=classroom, name__icontains='Lâm Uyển Như').first()
    
    print(f"Lớp: {classroom}")
    print(f"Học sinh: {student}")
    
    # Kiểm tra payment records
    payments = StudentPayment.objects.filter(student=student).order_by('month')
    
    for payment in payments:
        print(f"\n{'='*60}")
        print(f"📅 THÁNG {payment.month}")
        print(f"{'='*60}")
        
        print(f"💰 Đã đóng: {payment.amount_paid:,.0f}₫")
        print(f"🏫 Học phí: {payment.tuition_fee:,.0f}₫")
        print(f"🍽️ Giá ăn: {payment.meal_price.daily_price:,}₫/ngày")
        print(f"💳 Số dư hiện tại: {payment.remaining_balance:,.0f}₫")
        
        # Kiểm tra MealRecord
        year, month = payment.month.split('-')
        meal_records = MealRecord.objects.filter(
            student=student,
            date__year=int(year),
            date__month=int(month)
        ).order_by('date', 'meal_type')
        
        print(f"\n📝 CHI TIẾT BỮA ĂN THÁNG {payment.month}:")
        print(f"Số bữa ăn: {meal_records.count()}")
        
        if meal_records.count() > 0:
            total_meal_charge = 0
            breakfast_count = 0
            lunch_count = 0
            
            for record in meal_records:
                if record.meal_type == "Bữa sáng":
                    if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                        total_meal_charge += payment.meal_price.breakfast_price
                        breakfast_count += 1
                        print(f"   🍳 {record.date}: Bữa sáng - {record.status} (non_eat={record.non_eat}) → +{payment.meal_price.breakfast_price:,}₫")
                    else:
                        print(f"   🍳 {record.date}: Bữa sáng - {record.status} (non_eat={record.non_eat}) → +0₫ (nghỉ có phép)")
                elif record.meal_type == "Bữa trưa":
                    if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                        total_meal_charge += payment.meal_price.lunch_price
                        lunch_count += 1
                        print(f"   🍽️ {record.date}: Bữa trưa - {record.status} (non_eat={record.non_eat}) → +{payment.meal_price.lunch_price:,}₫")
                    else:
                        print(f"   🍽️ {record.date}: Bữa trưa - {record.status} (non_eat={record.non_eat}) → +0₫ (nghỉ có phép)")
            
            print(f"\n🍳 Tổng bữa sáng tính phí: {breakfast_count}")
            print(f"🍽️ Tổng bữa trưa tính phí: {lunch_count}")
            print(f"💵 Tổng tiền ăn: {total_meal_charge:,}₫")
            
            # Kiểm tra logic tính toán
            print(f"\n🔢 KIỂM TRA TÍNH TOÁN:")
            print(f"   amount_paid: {payment.amount_paid:,.0f}₫")
            print(f"   tuition_fee: {payment.tuition_fee:,.0f}₫")
            print(f"   total_meal_charge: {total_meal_charge:,}₫")
            
            # Tìm prior_remain_balance
            if payment.month != "2025-06":  # Không phải tháng đầu tiên
                dt = datetime.strptime(payment.month, '%Y-%m')
                prev_month = (dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
                prev_payment = StudentPayment.objects.filter(student=student, month=prev_month).order_by('-id').first()
                
                if prev_payment:
                    prior_balance = prev_payment.remaining_balance
                    print(f"   prior_remain_balance: {prior_balance:,.0f}₫ (từ tháng {prev_month})")
                else:
                    # Tìm tháng gần nhất có dữ liệu
                    prior = StudentPayment.objects.filter(student=student).exclude(month=payment.month).order_by('-month').first()
                    if prior:
                        prior_balance = prior.remaining_balance
                        print(f"   prior_remain_balance: {prior_balance:,.0f}₫ (từ tháng {prior.month})")
                    else:
                        prior_balance = 0
                        print(f"   prior_remain_balance: 0₫ (không có tháng trước)")
            else:
                prior_balance = 0
                print(f"   prior_remain_balance: 0₫ (tháng đầu tiên)")
            
            # Tính toán expected
            expected_balance = payment.amount_paid - payment.tuition_fee - Decimal(total_meal_charge) + prior_balance
            print(f"\n   Công thức: {payment.amount_paid:,.0f} - {payment.tuition_fee:,.0f} - {total_meal_charge:,} + {prior_balance:,.0f}")
            print(f"   Kết quả: {expected_balance:,.0f}₫")
            
            if payment.remaining_balance != expected_balance:
                print(f"   ⚠️ SỐ DƯ KHÔNG KHỚP!")
                print(f"      Tính toán: {expected_balance:,.0f}₫")
                print(f"      Thực tế: {payment.remaining_balance:,.0f}₫")
                print(f"      Chênh lệch: {abs(expected_balance - payment.remaining_balance):,.0f}₫")
            else:
                print(f"   ✅ Số dư tính đúng: {payment.remaining_balance:,.0f}₫")
        
        else:
            print(f"   📝 Không có bữa ăn nào trong tháng này")
    
    # Kiểm tra tổng thể
    print(f"\n{'='*60}")
    print(f"📊 TỔNG KẾT TỔNG THỂ")
    print(f"{'='*60}")
    
    total_paid = sum(p.amount_paid for p in payments)
    total_tuition = sum(p.tuition_fee for p in payments)
    total_balance = sum(p.remaining_balance for p in payments)
    
    print(f"💰 Tổng đã đóng: {total_paid:,.0f}₫")
    print(f"🏫 Tổng học phí: {total_tuition:,.0f}₫")
    print(f"💳 Tổng số dư: {total_balance:,.0f}₫")
    
    # Kiểm tra logic
    print(f"\n🔍 PHÂN TÍCH LOGIC:")
    print(f"Tháng 6: Nợ {payments[0].remaining_balance:,.0f}₫")
    print(f"Tháng 8: Nợ {payments[1].remaining_balance:,.0f}₫")
    
    if len(payments) >= 2:
        diff = payments[1].remaining_balance - payments[0].remaining_balance
        print(f"Chênh lệch: {diff:,.0f}₫")
        
        if diff > 0:
            print(f"⚠️ VẤN ĐỀ: Số nợ GIẢM {diff:,.0f}₫ mà không có lý do rõ ràng!")
        else:
            print(f"✅ Số nợ thay đổi hợp lý: {diff:,.0f}₫")

if __name__ == "__main__":
    from datetime import datetime, timedelta
    debug_payment()

