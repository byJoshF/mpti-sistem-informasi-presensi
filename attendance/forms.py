from django import forms

from .models import AttendanceSession, AttendanceRecord


class AttendanceSessionCreateForm(forms.Form):
    duration_minutes = forms.TypedChoiceField(
        choices=AttendanceSession.DURATION_CHOICES,
        coerce=int,
        label="Durasi sesi absensi"
    )


class AttendanceSessionCancelForm(forms.Form):
    reason = forms.CharField(
        min_length=5,
        max_length=500,
        label="Alasan pembatalan"
    )


class AttendanceCodeForm(forms.Form):
    attendance_code = forms.CharField(
        min_length=4,
        max_length=4,
        strip=True,
        label="Kode Absensi",
        widget=forms.TextInput(attrs={
            "placeholder": "Contoh: K7F2",
            "autocomplete": "off",
            "maxlength": "4",
        })
    )

    def clean_attendance_code(self):
        code = self.cleaned_data["attendance_code"].upper()
        letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
        digits = "23456789"

        valid = (
            len(code) == 4
            and code[0] in letters
            and code[1] in digits
            and code[2] in letters
            and code[3] in digits
        )

        if not valid:
            raise forms.ValidationError(
                "Format kode harus berupa huruf-angka-huruf-angka."
            )

        return code


class AttendanceRecordStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            (AttendanceRecord.Status.PRESENT, "Hadir"),
            (AttendanceRecord.Status.PERMITTED, "Izin"),
            (AttendanceRecord.Status.SICK, "Sakit"),
            (AttendanceRecord.Status.ABSENT, "Alfa"),
        ],
        label="Status kehadiran"
    )

    reason = forms.CharField(
        min_length=5,
        max_length=500,
        strip=True,
        label="Alasan perubahan",
        widget=forms.TextInput(attrs={
            "placeholder": "Masukkan alasan perubahan status",
            "autocomplete": "off",
        })
    )


class AttendanceRecapForm(forms.Form):
    start_date = forms.DateField(
        label="Tanggal awal semester",
        widget=forms.DateInput(attrs={
            "type": "date"
        })
    )

    end_date = forms.DateField(
        label="Tanggal akhir semester",
        widget=forms.DateInput(attrs={
            "type": "date"
        })
    )

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            self.add_error(
                "end_date",
                "Tanggal akhir tidak boleh lebih awal dari tanggal awal."
            )

        return cleaned_data