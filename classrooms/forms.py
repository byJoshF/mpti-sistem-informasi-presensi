from django import forms
from .models import Classroom


class ClassroomCreateForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ("name", "description")

        labels = {
            "name": "Nama kelas / mata kuliah",
            "description": "Deskripsi kelas",
        }

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Contoh: Manajemen Proyek TI"
            }),
            "description": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Keterangan kelas (opsional)"
            }),
        }


class JoinClassForm(forms.Form):
    join_code = forms.CharField(
        max_length=6,
        min_length=6,
        label="Kode Gabung",
        widget=forms.TextInput(attrs={
            "placeholder": "Contoh: K7F1H9",
            "autocomplete": "off",
        })
    )

    def clean_join_code(self):
        code = self.cleaned_data["join_code"].strip().upper()

        if not Classroom.objects.filter(join_code=code).exists():
            raise forms.ValidationError(
                "Kode kelas tidak ditemukan. Periksa kembali kode yang dimasukkan."
            )

        return code