from django import forms

from .models import DriverApplication, DriverDocument, DriverProfile, Vehicle, VehicleDocument


NATIONALITY_CHOICES = [
    ('Afghanistan', 'Afghanistan'),
    ('Albania', 'Albania'),
    ('Algeria', 'Algeria'),
    ('Angola', 'Angola'),
    ('Argentina', 'Argentina'),
    ('Australia', 'Australia'),
    ('Austria', 'Austria'),
    ('Belgium', 'Belgium'),
    ('Botswana', 'Botswana'),
    ('Brazil', 'Brazil'),
    ('Canada', 'Canada'),
    ('Chile', 'Chile'),
    ('China', 'China'),
    ('Colombia', 'Colombia'),
    ('Croatia', 'Croatia'),
    ('Cuba', 'Cuba'),
    ('Czech Republic', 'Czech Republic'),
    ('Denmark', 'Denmark'),
    ('Egypt', 'Egypt'),
    ('Ethiopia', 'Ethiopia'),
    ('Finland', 'Finland'),
    ('France', 'France'),
    ('Germany', 'Germany'),
    ('Ghana', 'Ghana'),
    ('Greece', 'Greece'),
    ('India', 'India'),
    ('Indonesia', 'Indonesia'),
    ('Ireland', 'Ireland'),
    ('Italy', 'Italy'),
    ('Jamaica', 'Jamaica'),
    ('Japan', 'Japan'),
    ('Kenya', 'Kenya'),
    ('Malawi', 'Malawi'),
    ('Malaysia', 'Malaysia'),
    ('Mexico', 'Mexico'),
    ('Mozambique', 'Mozambique'),
    ('Namibia', 'Namibia'),
    ('Netherlands', 'Netherlands'),
    ('New Zealand', 'New Zealand'),
    ('Nigeria', 'Nigeria'),
    ('Norway', 'Norway'),
    ('Pakistan', 'Pakistan'),
    ('Peru', 'Peru'),
    ('Philippines', 'Philippines'),
    ('Poland', 'Poland'),
    ('Portugal', 'Portugal'),
    ('Romania', 'Romania'),
    ('Russia', 'Russia'),
    ('Rwanda', 'Rwanda'),
    ('Saudi Arabia', 'Saudi Arabia'),
    ('Senegal', 'Senegal'),
    ('Singapore', 'Singapore'),
    ('South Africa', 'South Africa'),
    ('South Korea', 'South Korea'),
    ('Spain', 'Spain'),
    ('Sweden', 'Sweden'),
    ('Switzerland', 'Switzerland'),
    ('Tanzania', 'Tanzania'),
    ('Thailand', 'Thailand'),
    ('Tunisia', 'Tunisia'),
    ('Turkey', 'Turkey'),
    ('Uganda', 'Uganda'),
    ('Ukraine', 'Ukraine'),
    ('United Arab Emirates', 'United Arab Emirates'),
    ('United Kingdom', 'United Kingdom'),
    ('United States', 'United States'),
    ('Zambia', 'Zambia'),
    ('Zimbabwe', 'Zimbabwe'),
]


class DriverProfileForm(forms.ModelForm):
    nationality = forms.ChoiceField(
        choices=[('', 'Select your nationality')] + NATIONALITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = DriverProfile
        fields = [
            'first_name', 'middle_name', 'last_name', 'date_of_birth', 'gender', 'nationality',
            'phone_number', 'alternative_phone', 'email', 'residential_address', 'city', 'province',
            'emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_phone'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'residential_address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class IdentityVerificationForm(forms.ModelForm):
    class Meta:
        model = DriverApplication
        fields = ['identity_document_type', 'identity_document_number', 'issue_date', 'expiry_date', 'identity_document_file']
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'identity_document_file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
        }

    def clean_identity_document_file(self):
        file = self.cleaned_data.get('identity_document_file')
        if not file:
            return file
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if file.content_type not in allowed_types:
            raise forms.ValidationError('Only PDF, JPG, JPEG, and PNG files are allowed.')
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File size must be 5MB or smaller.')
        return file


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['vehicle_type', 'make', 'model', 'year', 'colour', 'registration_number', 'vin_chassis_number', 'max_cargo_capacity']
        widgets = {
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class DriverDocumentUploadForm(forms.Form):
    DOCUMENT_FIELDS = [
        ("Driver's Licence", 'drivers_licence'),
        ('Proof of Address', 'proof_of_address'),
        ('Driver Clearance', 'driver_clearance'),
        ('Additional Supporting Document', 'additional_supporting_document'),
    ]

    document_type = forms.ChoiceField(choices=DriverDocument.DOCUMENT_TYPES, required=False)
    file = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))
    drivers_licence = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))
    proof_of_address = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))
    driver_clearance = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))
    additional_supporting_document = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))

    def __init__(self, *args, **kwargs):
        self.application = kwargs.pop('application', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        document_type = cleaned_data.get('document_type')
        uploaded_file = cleaned_data.get('file')

        if uploaded_file and document_type and self.application:
            if DriverDocument.objects.filter(application=self.application, document_type=document_type).exists():
                self.add_error('document_type', f'{document_type} has already been uploaded for this application.')

        if self.application:
            for item_type, field_name in self.DOCUMENT_FIELDS:
                file_field = cleaned_data.get(field_name)
                if file_field and DriverDocument.objects.filter(application=self.application, document_type=item_type).exists():
                    self.add_error(field_name, f'{item_type} has already been uploaded for this application.')
        return cleaned_data

    def clean_document_type(self):
        return self.cleaned_data.get('document_type')

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            return file
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if file.content_type not in allowed_types:
            raise forms.ValidationError('Only PDF, JPG, JPEG, and PNG files are allowed.')
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File size must be 5MB or smaller.')
        return file

    def clean_drivers_licence(self):
        return self._clean_uploaded_file('drivers_licence')

    def clean_proof_of_address(self):
        return self._clean_uploaded_file('proof_of_address')

    def clean_driver_clearance(self):
        return self._clean_uploaded_file('driver_clearance')

    def clean_additional_supporting_document(self):
        return self._clean_uploaded_file('additional_supporting_document')

    def _clean_uploaded_file(self, field_name):
        file = self.cleaned_data.get(field_name)
        if not file:
            return file
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if file.content_type not in allowed_types:
            raise forms.ValidationError('Only PDF, JPG, JPEG, and PNG files are allowed.')
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File size must be 5MB or smaller.')
        return file


class VehicleDocumentUploadForm(forms.Form):
    DOCUMENT_FIELDS = [
        ('Vehicle Registration', 'vehicle_registration'),
        ('Vehicle Insurance', 'vehicle_insurance'),
        ('Vehicle Inspection', 'vehicle_inspection'),
    ]

    document_type = forms.ChoiceField(choices=VehicleDocument.DOCUMENT_TYPES, required=False)
    file = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))
    vehicle_registration = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))
    vehicle_insurance = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))
    vehicle_inspection = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))

    def __init__(self, *args, **kwargs):
        self.vehicle = kwargs.pop('vehicle', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        document_type = cleaned_data.get('document_type')
        uploaded_file = cleaned_data.get('file')

        if uploaded_file and document_type and self.vehicle:
            if VehicleDocument.objects.filter(vehicle=self.vehicle, document_type=document_type).exists():
                self.add_error('document_type', f'{document_type} has already been uploaded for this vehicle.')

        if self.vehicle:
            for item_type, field_name in self.DOCUMENT_FIELDS:
                file_field = cleaned_data.get(field_name)
                if file_field and VehicleDocument.objects.filter(vehicle=self.vehicle, document_type=item_type).exists():
                    self.add_error(field_name, f'{item_type} has already been uploaded for this vehicle.')
        return cleaned_data

    def clean_document_type(self):
        return self.cleaned_data.get('document_type')

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            return file
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if file.content_type not in allowed_types:
            raise forms.ValidationError('Only PDF, JPG, JPEG, and PNG files are allowed.')
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File size must be 5MB or smaller.')
        return file

    def clean_vehicle_registration(self):
        return self._clean_uploaded_file('vehicle_registration')

    def clean_vehicle_insurance(self):
        return self._clean_uploaded_file('vehicle_insurance')

    def clean_vehicle_inspection(self):
        return self._clean_uploaded_file('vehicle_inspection')

    def _clean_uploaded_file(self, field_name):
        file = self.cleaned_data.get(field_name)
        if not file:
            return file
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if file.content_type not in allowed_types:
            raise forms.ValidationError('Only PDF, JPG, JPEG, and PNG files are allowed.')
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File size must be 5MB or smaller.')
        return file


class DriverDocumentForm(DriverDocumentUploadForm):
    pass


class VehicleDocumentForm(VehicleDocumentUploadForm):
    pass


class ReviewConfirmationForm(forms.Form):
    confirm_accuracy = forms.BooleanField(required=True, label='I confirm that the information provided is accurate and that all uploaded documents are fictional test documents for this assessment.')
