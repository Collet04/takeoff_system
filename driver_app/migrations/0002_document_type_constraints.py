from django.db import migrations, models
from django.db.models import Count


def remove_duplicate_driver_documents(apps, schema_editor):
    DriverDocument = apps.get_model('driver_app', 'DriverDocument')
    for duplicate_group in DriverDocument.objects.values('application_id', 'document_type').annotate(total=Count('id')).filter(total__gt=1):
        rows = list(
            DriverDocument.objects.filter(
                application_id=duplicate_group['application_id'],
                document_type=duplicate_group['document_type'],
            ).order_by('uploaded_at', 'id')[1:]
        )
        for row in rows:
            row.delete()


def remove_duplicate_vehicle_documents(apps, schema_editor):
    VehicleDocument = apps.get_model('driver_app', 'VehicleDocument')
    for duplicate_group in VehicleDocument.objects.values('vehicle_id', 'document_type').annotate(total=Count('id')).filter(total__gt=1):
        rows = list(
            VehicleDocument.objects.filter(
                vehicle_id=duplicate_group['vehicle_id'],
                document_type=duplicate_group['document_type'],
            ).order_by('uploaded_at', 'id')[1:]
        )
        for row in rows:
            row.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('driver_app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_driver_documents, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(remove_duplicate_vehicle_documents, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='driverdocument',
            constraint=models.UniqueConstraint(
                fields=('application', 'document_type'),
                name='unique_driver_document_type_per_application',
            ),
        ),
        migrations.AddConstraint(
            model_name='vehicledocument',
            constraint=models.UniqueConstraint(
                fields=('vehicle', 'document_type'),
                name='unique_vehicle_document_type_per_vehicle',
            ),
        ),
    ]
