from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
# from .encryption import fernet  # We will handle encryption/decryption in views/forms, not here.


class ApiCredential(models.Model):
    """Stores encrypted API credentials for AI services like OpenRouter."""
    name = models.CharField(max_length=100, unique=True, help_text="A unique name for this credential.")
    api_key_encrypted = models.TextField(help_text="The API key, encrypted at rest.")
    service_provider = models.CharField(max_length=50, default="OpenRouter", help_text="The AI service provider.")
    is_active = models.BooleanField(default=True, help_text="Whether this credential can be used for new jobs.")
    is_free = models.BooleanField(default=False, help_text="Mark if the models under this key are free to use.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_masked_key(self):
        """Returns a masked version of the key for display purposes."""
        # This method assumes the key is stored decrypted in memory, which it isn't.
        # The actual decryption and masking will happen in the view/form layer.
        # For now, we return a static mask as the model itself can't decrypt.
        if self.api_key_encrypted:
            return "sk-..." + "xxxx" # A placeholder mask
        return ""

    class Meta:
        verbose_name = "API Credential"
        verbose_name_plural = "API Credentials"
        ordering = ['name']


class AppSetting(models.Model):
    """A singleton model to store global application settings."""
    max_file_size_mb = models.PositiveIntegerField(default=25, help_text="Maximum allowed file size in MB.")
    allowed_formats = models.CharField(
        max_length=200, default="pdf", help_text="Comma-separated list of allowed file extensions (e.g., 'pdf,docx')."
    )
    default_ai_model = models.CharField(
        max_length=100, blank=True, help_text="Default AI model to use for processing (e.g., 'openai/gpt-3.5-turbo')."
    )
    enable_ocr = models.BooleanField(
        default=False, help_text="Enable OCR for scanned PDFs (requires Tesseract)."
    )
    processing_concurrency = models.PositiveIntegerField(
        default=2, help_text="Number of files to process concurrently (if using Celery)."
    )

    def __str__(self):
        return "Application Settings"

    class Meta:
        verbose_name = "Application Setting"
        verbose_name_plural = "Application Settings"


class UploadedFile(models.Model):
    """Represents a file uploaded by a user."""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="The user who uploaded the file.")
    session_key = models.CharField(max_length=40, null=True, blank=True, help_text="Session key for anonymous users.")
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    filesize = models.PositiveIntegerField(help_text="File size in bytes.")
    filetype = models.CharField(max_length=100, help_text="MIME type of the file.")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename


class ProcessingJob(models.Model):
    """Tracks the state of a file being processed."""
    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        PROCESSING = 'processing', 'Processing'
        COMPLETE = 'complete', 'Complete'
        ERROR = 'error', 'Error'

    uploaded_file = models.OneToOneField(UploadedFile, on_delete=models.CASCADE, related_name='job')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    celery_task_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID of the Celery task, if applicable.")
    status_message = models.CharField(max_length=255, blank=True, null=True, help_text="Details on the current status (e.g., error message).")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Job for {self.uploaded_file.filename} ({self.status})"


class ProcessingResult(models.Model):
    """Stores the results of a successful processing job."""
    job = models.OneToOneField(ProcessingJob, on_delete=models.CASCADE, related_name='result')
    full_summary = models.TextField(blank=True)
    key_insights = models.TextField(blank=True, help_text="Bullet points or key takeaways.")
    flashcards = models.JSONField(default=list, blank=True, help_text="List of Q/A prompts, e.g., [{'q': '...', 'a': '...'}].")
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for {self.job.uploaded_file.filename}"


class UsageLog(models.Model):
    """Logs each processing job for analytics."""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    job = models.ForeignKey(ProcessingJob, on_delete=models.CASCADE)
    model_used = models.CharField(max_length=100)
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log for Job ID {self.job.id} at {self.timestamp}"


class AuditEntry(models.Model):
    """Logs administrative actions for security and audit trails."""
    user = models.ForeignKey(User, on_delete=models.PROTECT, help_text="Admin user who performed the action.")
    action = models.CharField(max_length=100, help_text="e.g., 'api_credential_create', 'settings_update'")
    details = models.TextField(blank=True, help_text="Description of the action taken.")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audit: {self.action} by {self.user.username} at {self.timestamp}"

    class Meta:
        verbose_name_plural = "Audit Entries"
        ordering = ['-timestamp']
