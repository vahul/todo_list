from django.test import TestCase

# Create your tests here.
from models import Task  # Import your model

# Delete all rows from the table
Task.objects.all().delete()
