from django.contrib import admin
from .models import Meeting, MeetingFile


class MeetingFileInline(admin.TabularInline):
    model = MeetingFile
    extra = 0
    fields = ('file_type', 'original_filename', 's3_key', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'created_at', 'updated_at', 'file_count')
    search_fields = ('title',)
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MeetingFileInline]

    def file_count(self, obj):
        return obj.files.count()
    file_count.short_description = 'Files'


@admin.register(MeetingFile)
class MeetingFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'meeting', 'file_type', 'original_filename', 's3_key', 'created_at')
    list_filter = ('file_type', 'created_at')
    search_fields = ('original_filename', 's3_key', 'meeting__title')
    readonly_fields = ('created_at',)
