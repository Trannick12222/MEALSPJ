from django.contrib import admin
from django.contrib import admin
from django import forms
from django.contrib.admin import AdminSite
from .models import MealRecord, Student, ClassRoom, StudentPayment,MealPrice,AuditLog
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.contrib import messages
from openpyxl import Workbook, load_workbook
import csv
from django.urls import reverse
import json
admin.site.site_header  = "Trang quản trị bữa ăn học sinh"
admin.site.site_title   = "Quản lý bữa ăn"
admin.site.index_title  = "Bảng điều khiển"

def log_admin_action(request, obj, action, extra=None):
    payload = {
        'model': obj._meta.label,
        'pk': obj.pk,
    }
    if extra:
        payload.update(extra)
    AuditLog.objects.create(
        user   = request.user,
        action = action,
        path   = request.path,
        data   = json.dumps(payload, ensure_ascii=False)
    )
class MealPriceAdmin(admin.ModelAdmin):
    list_display  = ('effective_date', 'daily_price', 'breakfast_price', 'lunch_price')
    list_editable = ('daily_price', 'breakfast_price', 'lunch_price')
    list_filter   = ('effective_date',)
    ordering      = ('-effective_date',)
class StudentInline(admin.TabularInline):
    model = Student
    extra = 0                 # không sinh form trống
    fields = ('name',)        # chỉ hiện tên (có thể thêm các field khác)
    show_change_link = True   # có link vào form edit của từng student
class MyAdminSite(AdminSite):
    site_header = "Trang quản trị bữa ăn học sinh"
    index_title = "Bảng điều khiển"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Đổ nhanh 2 link vào dashboard
        extra_context['quick_links'] = [
            {
                'url': reverse('meals:statistics'),
                'label': '📊 Thống kê'
            },
            {
                'url': reverse('meals:student_payment_edit'),
                'label': '💳 Chỉnh sửa công nợ'
            }
        ]
        return super().index(request, extra_context)

    # Tuỳ ý bạn có thể override get_urls để thêm view custom,
    # nhưng ở đây chỉ cần index.

class ClassNameFilter(admin.SimpleListFilter):
    title = 'Lớp học'
    parameter_name = 'class_name'

    def lookups(self, request, model_admin):
        class_names = Student.objects.values_list('class_name', flat=True).distinct()
        return [(cls, cls) for cls in class_names if cls]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(class_name=self.value())
        return queryset
class StudentPaymentAdminForm(forms.ModelForm):
    class Meta:
        model = StudentPayment
        fields = '__all__'
        widgets = {
            # HTML5 month-picker
            'month': forms.TextInput(attrs={'type': 'month'}),
        }
        def validate_unique(self):
            # chỉ giữ lại validate field-level (nếu có), skip toàn bộ unique_together
            try:
                # gọi bản gốc, nhưng sẽ không raise vì ta ignore
                super().validate_unique()
            except forms.ValidationError:
                pass
from django.contrib.admin import SimpleListFilter
class YearFilter(SimpleListFilter):
    title            = 'Năm'
    parameter_name   = 'year'

    def lookups(self, request, model_admin):
        # Lấy tập hợp các năm từ giá trị month “YYYY-MM”
        months = model_admin.model.objects.values_list('month', flat=True).distinct()
        years = sorted({m.split('-')[0] for m in months}, reverse=True)
        return [(y, y) for y in years]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(month__startswith=self.value() + '-')
        return queryset
class MonthFilter(SimpleListFilter):
    title            = 'Tháng'
    parameter_name   = 'month'

    def lookups(self, request, model_admin):
        year = request.GET.get('year')
        # chỉ lấy những month thuộc năm đã chọn (nếu có)
        months = model_admin.model.objects.values_list('month', flat=True).distinct()
        if year:
            months = [m for m in months if m.startswith(f"{year}-")]
        # chuyển thành list duy nhất, sort tăng dần
        unique = sorted({m for m in months})
        # trả về tuple (value, label) — ở đây label chỉ lấy phần MM
        return [(m, m.split('-')[1]) for m in unique]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(month=self.value())
        return queryset       
class StudentPaymentAdmin(admin.ModelAdmin):
    form = StudentPaymentAdminForm
    list_display  = (
        'student',
        'month',
        'tuition_fee_fmt',
        'meal_price',            # nếu đã override __str__ là "YYYY-MM-DD → X,000đ/ngày"
        'amount_paid_fmt',
        'remaining_balance_fmt',
    )
    search_fields = ('student__name','month')   # ← tìm theo tên học sinh hoặc tháng
    
    list_filter   = (YearFilter,'student__classroom',MonthFilter)  
    verbose_name  = "Công nợ học sinh"
    verbose_name_plural = "Công nợ học sinh"
    @admin.display(ordering='tuition_fee', description='Học phí')
    def tuition_fee_fmt(self, obj):
        return f"{obj.tuition_fee:,.0f}"

    @admin.display(ordering='amount_paid', description='Số tiền đã đóng')
    def amount_paid_fmt(self, obj):
        return f"{obj.amount_paid:,.0f}"

    @admin.display(ordering='remaining_balance', description='Số dư')
    def remaining_balance_fmt(self, obj):
        return f"{obj.remaining_balance:,.0f}"
    def save_model(self, request, obj, form, change):
        existing = StudentPayment.objects.filter(
            student=obj.student,
            month=obj.month
        ).exclude(pk=obj.pk).first()

        if existing:
            # ghi đè lên existing
            existing.tuition_fee    = obj.tuition_fee
            existing.meal_price     = obj.meal_price
            existing.amount_paid    = obj.amount_paid
            existing.save()
            self.message_user(request, f"✅ Đã cập nhật bản ghi {existing.id}.", level=messages.SUCCESS)
            target = existing
        else:
            super().save_model(request, obj, form, change)
            target = obj

        # always log both add & change
        action = 'change_payment' if change else 'add_payment'
        log_admin_action(request, target, action,
                         extra={'changed_fields': form.changed_data})

    def delete_model(self, request, obj):
        log_admin_action(request, obj, 'delete_payment')
        super().delete_model(request, obj)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [StudentInline]  
    verbose_name = "Lớp học"
    verbose_name_plural = "Các lớp học"
    change_form_template = "admin/meals/classroom_change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<int:classroom_id>/delete_students/',
                self.admin_site.admin_view(self.delete_students_view),
                name='meals_classroom_delete_students'
            ),
            path(
                '<int:classroom_id>/export_students/',
                self.admin_site.admin_view(self.export_students_view),
                name='meals_classroom_export_students'
            ),
            path(
                '<int:classroom_id>/import_students/',
                self.admin_site.admin_view(self.import_students_view),
                name='meals_classroom_import_students'
            ),
        ]
        # Đặt custom URLs lên trước để không bị chặn bởi mặc định
        return custom + urls
    def delete_students_view(self, request, classroom_id):
        room = ClassRoom.objects.get(pk=classroom_id)
        if request.method == 'POST':
            # xóa tất cả sinh viên trong lớp, cascades luôn MealRecord & StudentPayment
            qs = Student.objects.filter(classroom=room)
            count, _ = qs.delete()
            self.message_user(request, f"Đã xóa {count} học sinh (và dữ liệu liên quan) của lớp {room.name}.")
            return HttpResponseRedirect(f'../../{classroom_id}/change/')

        context = {
            **self.admin_site.each_context(request),
            'opts':    self.model._meta,
            'original': room,
            'title':   f'Xác nhận xóa toàn bộ học sinh lớp “{room.name}”',
        }
        return TemplateResponse(request, "admin/meals/classroom_delete_students_confirmation.html", context)
    
    def export_students_view(self, request, classroom_id):
        room = ClassRoom.objects.get(pk=classroom_id)
        qs = Student.objects.filter(classroom=room).order_by('name')

        # Tạo workbook và sheet
        wb = Workbook()
        ws = wb.active
        ws.title = 'Học sinh'

        # Header
        ws.append(['Tên học sinh'])

        # Dữ liệu
        for s in qs:
            ws.append([s.name])

        # Xuất file .xlsx
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"students_{room.name}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # log thêm/sửa lớp
        action = 'change_classroom' if change else 'add_classroom'
        log_admin_action(request, obj, action,
                         extra={'changed_fields': form.changed_data})
    
    def delete_model(self, request, obj):
        log_admin_action(request, obj, 'delete_classroom')
        super().delete_model(request, obj)
    def import_students_view(self, request, classroom_id):
        room = ClassRoom.objects.get(pk=classroom_id)

        if request.method == 'POST':
            excel_file = request.FILES.get('excel_file')
            if not excel_file:
                self.message_user(request, "⚠️ Chưa chọn file Excel.", level=messages.ERROR)
                return HttpResponseRedirect(request.path)

            # Đọc workbook
            wb = load_workbook(filename=excel_file, read_only=True, data_only=True)
            ws = wb.active

            count = 0
            # Bắt đầu từ row 2 để bỏ header
            for row in ws.iter_rows(min_row=2, values_only=True):
                name = row[0]
                if name and str(name).strip():
                    Student.objects.get_or_create(name=str(name).strip(), classroom=room)
                    count += 1

            self.message_user(request, f"✅ Imported {count} học sinh vào lớp {room.name}.",
                               level=messages.SUCCESS)
            return HttpResponseRedirect(f'../../{classroom_id}/change/')

        # GET: render form
        context = {
            **self.admin_site.each_context(request),
            'opts':     self.model._meta,
            'original': room,
            'title':    f'Import học sinh cho lớp “{room.name}”',
        }
        return TemplateResponse(request, "admin/meals/import_students.html", context)

class StudentAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = ('classroom',)
    # Đổi tên hiển thị của model Student trong Admin
    verbose_name = "Học sinh"
    verbose_name_plural = "Các học sinh"
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # log thêm/sửa học sinh, kèm tên và lớp
        action = 'change_student' if change else 'add_student'
        log_admin_action(request, obj, action, extra={
            'student_name': obj.name,
            'classroom':    obj.classroom.name if obj.classroom else None,
            # nếu vẫn muốn xem fields nào change thì thêm tiếp:
            'changed_fields': form.changed_data
        })

    def delete_model(self, request, obj):
        # Lưu tên + lớp trước khi nó bị xóa
        student_name = obj.name
        classroom    = obj.classroom.name if obj.classroom else ''
        # Ghi log với extra chứa name và classroom
        log_admin_action(request, obj, 'delete_student', extra={
            'student_name': student_name,
            'classroom':    classroom
        })
        super().delete_model(request, obj)

class MealRecordAdmin(admin.ModelAdmin):
    change_list_template = "admin/meals/mealrecord/change_list.html"
    list_display = ('student', 'date', 'meal_type', 'status')
    fields = ('student','date','meal_type','status','non_eat','absence_reason')
    list_filter = ('date', 'meal_type','student__classroom')
    date_hierarchy = 'date'
    search_fields = ('student__name',)
    # Đổi tên hiển thị của model MealRecord trong Admin
    verbose_name = "Bữa ăn"
    verbose_name_plural = "Các bữa ăn"
    def delete_model(self, request, obj):
        log_admin_action(request, obj, 'delete_mealrecord')
        super().delete_model(request, obj)
    def save_model(self, request, obj, form, change):
        existing_record = MealRecord.objects.filter(
             student=obj.student,
             date=obj.date,
             meal_type=obj.meal_type
        ).first()
        if existing_record:
            existing_record.status         = obj.status
            existing_record.non_eat        = obj.non_eat
            existing_record.absence_reason = obj.absence_reason
            existing_record.save()
            target = existing_record
        else:
            super().save_model(request, obj, form, change)
            target = obj

        # log hành động bữa ăn (add/change)
        action = 'change_mealrecord' if change else 'add_mealrecord'
        log_admin_action(request, target, action,
                         extra={'status': obj.status, 'non_eat': obj.non_eat})
        
        # Xác định chuỗi "YYYY-MM" từ obj.date
        year_month = obj.date.strftime("%Y-%m")
        from .models import StudentPayment
        try:
            sp = StudentPayment.objects.get(student=obj.student, month=year_month)
            sp.save()  # gọi model.save() sẽ dùng meal_price để tính remaining_balance
        except StudentPayment.DoesNotExist:
            pass
        
class MealRecordAdminForm(forms.ModelForm):
    class Meta:
        model = MealRecord
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 1) disable non_eat nếu status="Đủ"
        if self.instance and self.instance.status == "Đủ":
            self.fields['non_eat'].disabled = True
        # 2) ẩn luôn absence_reason nếu non_eat==0
        if self.instance and self.instance.non_eat == 0:
            self.fields.pop('absence_reason', None)
    
admin.site.register(ClassRoom, ClassRoomAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(MealRecord, MealRecordAdmin)
# Khởi tạo site mới
my_admin_site = MyAdminSite(name='myadmin')

# Đăng ký các model với site mới
from .admin import MealRecordAdmin  # form tuỳ chỉnh bạn đã có
my_admin_site.register(MealRecord, MealRecordAdmin)
try:
    my_admin_site.unregister(ClassRoom)
    my_admin_site.unregister(Student)
    my_admin_site.unregister(StudentPayment)
except:
    pass
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user_display', 'action', 'path')
    readonly_fields = ('user','action','path','data','timestamp')
    ordering        = ('-timestamp',)
    def user_display(self, obj):
        return obj.user.username if obj.user else '—'
    user_display.short_description = 'User'
my_admin_site.register(StudentPayment, StudentPaymentAdmin)
# đăng ký ClassRoomAdmin lên my_admin_site
my_admin_site.register(ClassRoom, ClassRoomAdmin)
my_admin_site.register(Student, StudentAdmin)
# Đăng ký thêm StudentPayment nếu muốn
my_admin_site.register(User, UserAdmin)
my_admin_site.register(Group, GroupAdmin)
my_admin_site.register(MealPrice, MealPriceAdmin)
my_admin_site.register(AuditLog, AuditLogAdmin)