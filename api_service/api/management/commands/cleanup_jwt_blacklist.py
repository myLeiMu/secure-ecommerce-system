from django.core.management.base import BaseCommand
from api_service.utils.jwt_balcklist import jwt_blacklist


class Command(BaseCommand):
    help = '清理JWT黑名单和显示统计信息'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='清理过期的黑名单令牌',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='显示黑名单统计信息',
        )

    def handle(self, *args, **options):
        if options['cleanup']:
            self.cleanup_blacklist()

        if options['stats']:
            self.show_stats()

        if not options['cleanup'] and not options['stats']:
            # 默认显示统计信息
            self.show_stats()

    def cleanup_blacklist(self):
        """清理黑名单"""
        try:
            cleaned_count = jwt_blacklist.cleanup_expired_tokens()
            self.stdout.write(
                self.style.SUCCESS(f'成功清理 {cleaned_count} 个过期令牌')
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'清理黑名单失败: {e}'))

    def show_stats(self):
        """显示统计信息"""
        try:
            size = jwt_blacklist.get_blacklist_size()
            info = jwt_blacklist.get_blacklist_info()

            self.stdout.write(
                self.style.SUCCESS('JWT黑名单统计信息:')
            )
            self.stdout.write(f"   总令牌数: {info.get('total_tokens', 0)}")
            self.stdout.write(f"   有效令牌数: {info.get('valid_tokens', 0)}")
            self.stdout.write(f"   过期令牌数: {info.get('expired_tokens', 0)}")
            self.stdout.write(f"   平均TTL: {info.get('avg_ttl_minutes', 0):.2f} 分钟")

            # 显示详细建议
            expired_count = info.get('expired_tokens', 0)
            if expired_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'有 {expired_count} 个过期令牌需要清理，使用 --cleanup 清理')
                )
            elif info.get('total_tokens', 0) > 0:
                self.stdout.write(
                    self.style.SUCCESS('所有令牌都在有效期内')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('黑名单为空')
                )

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'获取统计信息失败: {e}'))
