from django.db import models


class Meeting(models.Model):
    """
    Represents a meeting session.
    Associated audio, transcript, and summary files are linked via MeetingFile.
    """
    title = models.CharField(
        max_length=255,
        help_text="Title or subject of the meeting"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the meeting was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the meeting was last updated"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Meeting'
        verbose_name_plural = 'Meetings'
        indexes = [
            models.Index(fields=['-created_at'], name='meeting_created_idx'),
        ]

    def __str__(self):
        return self.title


class MeetingFile(models.Model):
    """
    Stores metadata and S3 object keys for files related to a Meeting.
    Actual file contents (audio recordings, text transcripts, summaries)
    are stored in AWS S3, never directly in the database.
    """
    class FileType(models.TextChoices):
        AUDIO = 'audio', 'Audio'
        TRANSCRIPT = 'transcript', 'Transcript'
        SUMMARY = 'summary', 'Summary'

    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='files',
        help_text="The meeting this file belongs to"
    )
    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices,
        help_text="Category of file: audio, transcript, or summary"
    )
    s3_key = models.CharField(
        max_length=1024,
        help_text="AWS S3 object key where the file is stored"
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original uploaded or recorded filename"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this file was uploaded/created"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Meeting File'
        verbose_name_plural = 'Meeting Files'
        indexes = [
            models.Index(fields=['meeting', 'file_type'], name='meeting_file_type_idx'),
            models.Index(fields=['file_type'], name='file_type_idx'),
            models.Index(fields=['s3_key'], name='file_s3_key_idx'),
            models.Index(fields=['-created_at'], name='file_created_idx'),
        ]

    def __str__(self):
        return f"{self.meeting.title} - {self.get_file_type_display()} ({self.original_filename})"
