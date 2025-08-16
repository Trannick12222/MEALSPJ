#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meals_system.settings')
django.setup()

from meals.models import Student, ClassRoom, StudentPayment, MealRecord
from decimal import Decimal

def check_student_payment():
    print("=== KIỂM TRA HỌC SINH LÂM UYỂN NHƯ ===")
    
    # Tìm lớp Cat Hè 2025
    classroom = ClassRoom.objects.filter(name='Cat', term='Hè 2025').first()
    if not classroom:
        print("❌ Không tìm thấy lớp Cat Hè 2025")
        return
    
    print(f"✅ Tìm thấy lớp: {classroom}")
    
    # Tìm học sinh Lâm Uyển Như
    student = Student.objects.filter(
        classroom=classroom, 
        name__icontains='Lâm Uyển Như'
    ).first()
    
    if not student:
        print("❌ Không tìm thấy học sinh Lâm Uyển Như trong lớp này")
        return
    
    print(f"✅ Tìm thấy học sinh: {student}")
    
    # Kiểm tra tất cả payment records
    payments = StudentPayment.objects.filter(student=student).order_by('month')
    print(f"\n📊 Số payment records: {payments.count()}")
    
    if payments.count() == 0:
        print("⚠️ Học sinh này chưa có payment records nào")
        return
    
    print("\n" + "="*80)
    print(f"{'Tháng':<12} {'Đã đóng':<15} {'Học phí':<15} {'Số dư':<15} {'Giá ăn':<15}")
    print("="*80)
    
    for payment in payments:
        meal_price_info = f"{payment.meal_price.daily_price:,}₫/ngày" if payment.meal_price else "N/A"
        print(f"{payment.month:<12} {payment.amount_paid:>12,.0f}₫ {payment.tuition_fee:>12,.0f}₫ {payment.remaining_balance:>12,.0f}₫ {meal_price_info:<15}")
    
    print("="*80)
    
    # Kiểm tra chi tiết từng tháng
    print("\n🔍 CHI TIẾT TỪNG THÁNG:")
    for payment in payments:
        print(f"\n📅 Tháng {payment.month}:")
        print(f"   💰 Đã đóng: {payment.amount_paid:,.0f}₫")
        print(f"   🏫 Học phí: {payment.tuition_fee:,.0f}₫")
        print(f"   🍽️ Giá ăn: {payment.meal_price.daily_price:,}₫/ngày" if payment.meal_price else "   🍽️ Giá ăn: N/A")
        
        # Kiểm tra MealRecord của tháng này
        year, month = payment.month.split('-')
        meal_records = MealRecord.objects.filter(
            student=student,
            date__year=int(year),
            date__month=int(month)
        ).order_by('date', 'meal_type')
        
        if meal_records.count() > 0:
            print(f"   📝 Số bữa ăn: {meal_records.count()}")
            
            # Tính tổng tiền ăn thực tế
            total_meal_charge = 0
            breakfast_count = 0
            lunch_count = 0
            
            for record in meal_records:
                if record.meal_type == "Bữa sáng":
                    if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                        total_meal_charge += payment.meal_price.breakfast_price
                        breakfast_count += 1
                elif record.meal_type == "Bữa trưa":
                    if record.status == "Đủ" or (record.status == "Thiếu" and record.non_eat == 2):
                        total_meal_charge += payment.meal_price.lunch_price
                        lunch_count += 1
            
            print(f"   🍳 Bữa sáng: {breakfast_count} bữa")
            print(f"   🍽️ Bữa trưa: {lunch_count} bữa")
            print(f"   💵 Tổng tiền ăn: {total_meal_charge:,}₫")
            
            # Kiểm tra tính toán
            expected_balance = payment.amount_paid - payment.tuition_fee - Decimal(total_meal_charge)
            if payment.remaining_balance != expected_balance:
                print(f"   ⚠️ SỐ DƯ KHÔNG KHỚP!")
                print(f"      Tính toán: {expected_balance:,.0f}₫")
                print(f"      Thực tế: {payment.remaining_balance:,.0f}₫")
                print(f"      Chênh lệch: {abs(expected_balance - payment.remaining_balance):,.0f}₫")
            else:
                print(f"   ✅ Số dư tính đúng: {payment.remaining_balance:,.0f}₫")
        else:
            print(f"   📝 Không có bữa ăn nào trong tháng này")
    
    # Tổng kết
    print(f"\n📈 TỔNG KẾT:")
    total_paid = sum(p.amount_paid for p in payments)
    total_tuition = sum(p.tuition_fee for p in payments)
    total_balance = sum(p.remaining_balance for p in payments)
    
    print(f"   💰 Tổng đã đóng: {total_paid:,.0f}₫")
    print(f"   🏫 Tổng học phí: {total_tuition:,.0f}₫")
    print(f"   💳 Tổng số dư: {total_balance:,.0f}₫")

if __name__ == "__main__":
    check_student_payment()

