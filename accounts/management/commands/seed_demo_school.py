import os
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academics.models import ClassTeacher, Section, Standard
from attendance.models import Attendance, StaffAttendance, TeacherAttendance
from school.models import AcademicYear, Institution, School
from schooladmin.models import AdminProfile
from staff.models import NonTeachingStaff
from students.models import Enrollment, Student, StudentRolePermission
from subjects.models import Subject
from teachers.models import Teacher


SUBJECT_NAMES = ['Mathematics', 'English', 'Science', 'Social Science', 'Tamil']
STAFF_ROLES = [
    'admin_staff', 'finance_staff', 'it_staff', 'operations_staff',
    'hostel_warden', 'transport_staff', 'external_staff', 'operations_staff',
]


def recent_weekdays(count=5):
    values = []
    current = timezone.localdate()
    while len(values) < count:
        if current.weekday() < 5:
            values.append(current)
        current -= timedelta(days=1)
    return list(reversed(values))


class Command(BaseCommand):
    help = 'Create an idempotent, synthetic Demo School dataset for the public demo environment.'

    @transaction.atomic
    def handle(self, *args, **options):
        if os.getenv('DEMO_MODE', '').strip().lower() not in {'1', 'true', 'yes', 'on'}:
            raise CommandError('Set DEMO_MODE=true before creating public demo data.')

        admin_email = os.getenv('DEMO_ADMIN_EMAIL', 'demo.admin@demo.example.test').strip().lower()
        admin_password = os.getenv('DEMO_ADMIN_PASSWORD', '')
        if not admin_password or len(admin_password) < 12:
            raise CommandError('Set DEMO_ADMIN_PASSWORD to a value with at least 12 characters.')

        institution, _ = Institution.objects.get_or_create(
            name='Demo Institution',
            defaults={
                'address': 'Demo Avenue, Chennai',
                'contact_phone': '0000000000',
                'contact_email': 'contact@demo-school.example.test',
            },
        )
        school, _ = School.objects.get_or_create(
            code='DEMO-SCHOOL',
            defaults={
                'institution': institution,
                'name': 'Demo School',
                'address': 'Demo Avenue, Chennai',
                'contact_phone': '0000000000',
                'contact_email': 'contact@demo-school.example.test',
                'is_active': True,
            },
        )
        if school.institution_id != institution.id:
            school.institution = institution
            school.save(update_fields=['institution'])

        academic_year, _ = AcademicYear.objects.get_or_create(
            school=school,
            name='2026-2027',
            defaults={
                'start_date': date(2026, 4, 1),
                'end_date': date(2027, 3, 31),
                'is_current': True,
            },
        )
        if not academic_year.is_current:
            academic_year.is_current = True
            academic_year.save(update_fields=['is_current'])

        standards = {}
        sections = {}
        for grade in range(1, 13):
            standard, _ = Standard.objects.get_or_create(
                school=school,
                name=str(grade),
                defaults={'description': f'Demo Class {grade}'},
            )
            standards[grade] = standard
            for section_name in ('A', 'B'):
                section, _ = Section.objects.get_or_create(
                    standard=standard,
                    name=section_name,
                    defaults={'school': school},
                )
                sections[(grade, section_name)] = section

            for subject_index, subject_name in enumerate(SUBJECT_NAMES, start=1):
                Subject.objects.get_or_create(
                    standard=standard,
                    name=subject_name,
                    defaults={'subject_code': f'DEMO-{grade:02d}-{subject_index:02d}'},
                )

        teachers = {}
        for teacher_index, (grade, section_name) in enumerate(
            ((grade, section) for grade in range(1, 13) for section in ('A', 'B')),
            start=1,
        ):
            teacher_id = f'DMT{teacher_index:03d}'
            teacher, _ = Teacher.objects.get_or_create(
                school=school,
                teacher_id=teacher_id,
                defaults={
                    'name': f'Demo Teacher {teacher_index}',
                    'email': f'{teacher_id.lower()}@demo.example.test',
                    'phone': f'000000{teacher_index:04d}',
                    'date_of_birth': date(1985, 1, 1) + timedelta(days=teacher_index),
                    'joining_date': date(2020, 6, 1),
                    'qualification': 'B.Ed',
                    'department': SUBJECT_NAMES[(teacher_index - 1) % len(SUBJECT_NAMES)],
                    'address': 'Demo Address',
                },
            )
            teachers[(grade, section_name)] = teacher
            ClassTeacher.objects.get_or_create(
                academic_year=academic_year,
                section=sections[(grade, section_name)],
                defaults={'teacher': teacher, 'school': school},
            )

        students = []
        enrollments = []
        student_index = 0
        for grade in range(1, 13):
            for section_name in ('A', 'B'):
                for section_student in range(1, 3):
                    student_index += 1
                    student_id = f'DMS{grade:02d}{section_name}{section_student:02d}'
                    parent_phone = f'000001{student_index:04d}'
                    student, _ = Student.objects.get_or_create(
                        school=school,
                        student_id=student_id,
                        defaults={
                            'student_name': f'Demo Student {student_index:03d}',
                            'student_email': f'{student_id.lower()}@demo.example.test',
                            'father_name': f'Demo Parent {student_index:03d}',
                            'mother_name': f'Demo Parent {student_index:03d} Mother',
                            'father_phone': parent_phone,
                            'mother_phone': f'000002{student_index:04d}',
                            'date_of_birth': date(2012, 1, 1) + timedelta(days=student_index),
                            'gender': 'Male' if student_index % 2 else 'Female',
                            'accommodation': 'day_scholar',
                            'standard': standards[grade],
                            'section': sections[(grade, section_name)],
                            'date_of_admission': date(2026, 4, 1),
                            'address': 'Demo Address',
                        },
                    )
                    students.append(student)
                    enrollment, _ = Enrollment.objects.get_or_create(
                        student=student,
                        academic_year=academic_year,
                        defaults={
                            'school': school,
                            'standard': standards[grade],
                            'section': sections[(grade, section_name)],
                            'is_active': True,
                        },
                    )
                    enrollments.append(enrollment)

        staff_members = []
        for staff_index in range(1, 9):
            staff_id = f'DMSF{staff_index:02d}'
            member, _ = NonTeachingStaff.objects.get_or_create(
                school=school,
                staff_id=staff_id,
                defaults={
                    'name': f'Demo Staff {staff_index}',
                    'phone': f'000003{staff_index:04d}',
                    'joining_date': date(2021, 6, 1),
                    'role': STAFF_ROLES[staff_index - 1],
                    'email': f'{staff_id.lower()}@demo.example.test',
                    'address': 'Demo Address',
                },
            )
            staff_members.append(member)

        User = get_user_model()
        admin, created = User.objects.get_or_create(
            username=admin_email,
            defaults={
                'email': admin_email,
                'first_name': 'Demo School Admin',
                'user_type': 'admin',
                'is_active': True,
            },
        )
        if not created and admin.user_type != 'admin':
            raise CommandError('DEMO_ADMIN_EMAIL is already assigned to a non-admin account.')
        if created or not admin.check_password(admin_password):
            admin.set_password(admin_password)
        admin.email = admin_email
        admin.is_active = True
        admin.save()
        AdminProfile.objects.update_or_create(user=admin, defaults={'school': school})
        StudentRolePermission.objects.get_or_create(school=school)

        attendance_dates = recent_weekdays()
        for enrollment_index, enrollment in enumerate(enrollments):
            for day_index, attendance_date in enumerate(attendance_dates):
                statuses = ('Present', 'Present', 'Late', 'Absent', 'Present')
                status_value = statuses[(day_index + enrollment_index) % len(statuses)]
                Attendance.objects.get_or_create(
                    enrollment=enrollment,
                    date=attendance_date,
                    defaults={'status': status_value},
                )

        for teacher_index, teacher in enumerate(teachers.values()):
            for day_index, attendance_date in enumerate(attendance_dates):
                status_value = ('Present', 'Present', 'Late', 'Absent', 'Present')[
                    (day_index + teacher_index) % 5
                ]
                TeacherAttendance.objects.get_or_create(
                    teacher=teacher,
                    date=attendance_date,
                    defaults={'status': status_value},
                )

        for staff_index, member in enumerate(staff_members):
            for day_index, attendance_date in enumerate(attendance_dates):
                status_value = ('Present', 'Present', 'Late', 'Absent', 'Present')[
                    (day_index + staff_index) % 5
                ]
                StaffAttendance.objects.get_or_create(
                    staff=member,
                    date=attendance_date,
                    defaults={'status': status_value},
                )

        school.total_students = len(students)
        school.total_teachers = len(teachers)
        school.total_non_teaching = len(staff_members)
        school.total_staffs = len(teachers) + len(staff_members)
        school.save(update_fields=[
            'total_students', 'total_teachers', 'total_non_teaching', 'total_staffs',
        ])

        self.stdout.write(self.style.SUCCESS(
            'Demo data is ready: 1 school, 12 classes, 24 sections, 24 teachers, '
            '48 students, 8 staff, subjects, and 5 weekdays of student/teacher/staff attendance.'
        ))
