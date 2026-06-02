from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from audit.models import AuditLog

class Command(BaseCommand):
    help = 'Delete audit logs older than retention period'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to retain (default: 90)'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion (required for production)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--archive',
            action='store_true',
            help='Archive to JSON instead of deleting (future feature)'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find logs older than retention period
        old_logs = AuditLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'No audit logs older than {days} days to delete.')
            )
            return
        
        # Show what would be deleted in dry-run mode
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] Would delete {count} audit logs older than {days} days.')
            )
            return
        
        # Require confirmation before deletion
        if not options['confirm']:
            self.stderr.write(
                self.style.ERROR(f'Would delete {count} audit logs older than {days} days. Use --confirm to proceed.')
            )
            return
        
        # Delete old logs with error handling
        try:
            old_logs.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {count} audit logs older than {days} days.'
                )
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error deleting logs: {str(e)}')
            )