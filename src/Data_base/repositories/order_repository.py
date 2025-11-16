from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, func
from datetime import datetime
from src.Data_base.models.order import Order, OrderItem, Payment, OrderStatus, PaymentStatus
from src.Data_base.repositories.base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository[Order]):
    """订单数据访问层"""

    def __init__(self, db: Session):
        super().__init__(Order, db)

    def create_order_with_items(self, order_data: dict, items_data: list) -> Optional[Order]:
        """创建订单和订单项（事务保护数据一致性）"""
        try:
            # 开始事务
            order = Order(**order_data)
            self.db.add(order)
            self.db.flush()  # 获取order_id但不提交

            # 添加订单项
            for item_data in items_data:
                item_data['order_id'] = order.order_id
                order_item = OrderItem(**item_data)
                self.db.add(order_item)

            self.db.commit()
            logger.info(f"创建订单成功: {order.order_number}, 订单项数: {len(items_data)}")
            return order
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建订单失败: {str(e)}")
            return None

    def get_order_with_details(self, order_id: int) -> Optional[Order]:
        """获取订单详情（包含订单项和商品信息）"""
        try:
            order = self.db.query(Order).options(
                joinedload(Order.order_items).joinedload(OrderItem.product),
                joinedload(Order.user),
                joinedload(Order.shipping_address),
                joinedload(Order.payment)
            ).filter(Order.order_id == order_id).first()

            logger.debug(f"获取订单详情: {order_id}")
            return order
        except Exception as e:
            logger.error(f"获取订单详情失败: {str(e)}")
            return None

    def get_user_orders(self, user_id: int, skip: int = 0, limit: int = 50) -> List[Order]:
        """获取用户订单列表"""
        try:
            orders = self.db.query(Order).options(
                joinedload(Order.order_items).joinedload(OrderItem.product)
            ).filter(
                Order.user_id == user_id
            ).order_by(desc(Order.created_at)).offset(skip).limit(limit).all()

            logger.debug(f"获取用户 {user_id} 的订单列表, 数量: {len(orders)}")
            return orders
        except Exception as e:
            logger.error(f"获取用户订单失败: {str(e)}")
            return []

    def update_order_status(self, order_id: int, new_status: OrderStatus,
                            reason: str = None) -> bool:
        """更新订单状态（带审计日志）"""
        try:
            order = self.get_by_id(order_id)
            if order:
                old_status = order.order_status
                order.order_status = new_status

                # 根据状态更新相应时间字段
                now = datetime.now()
                if new_status == OrderStatus.SHIPPED and not order.shipped_date:
                    order.shipped_date = now
                elif new_status == OrderStatus.DELIVERED and not order.delivered_date:
                    order.delivered_date = now
                elif new_status == OrderStatus.CANCELLED and not order.cancelled_date:
                    order.cancelled_date = now

                self.db.commit()
                logger.info(f"更新订单状态: {order_id} {old_status}->{new_status}, 原因: {reason}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新订单状态失败: {str(e)}")
            return False

    def get_orders_by_status(self, status: OrderStatus, skip: int = 0, limit: int = 100) -> List[Order]:
        """根据状态获取订单"""
        try:
            orders = self.db.query(Order).options(
                joinedload(Order.user)
            ).filter(
                Order.order_status == status
            ).order_by(asc(Order.created_at)).offset(skip).limit(limit).all()

            logger.debug(f"获取状态为 {status} 的订单, 数量: {len(orders)}")
            return orders
        except Exception as e:
            logger.error(f"按状态获取订单失败: {str(e)}")
            return []

    def get_sales_statistics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """获取销售统计（复杂查询示例）"""
        try:
            # 总销售额
            total_sales = self.db.query(func.sum(Order.total_amount)).filter(
                Order.order_status.in_([OrderStatus.CONFIRMED, OrderStatus.DELIVERED]),
                Order.created_at.between(start_date, end_date)
            ).scalar() or 0

            # 订单数量
            order_count = self.db.query(func.count(Order.order_id)).filter(
                Order.order_status.in_([OrderStatus.CONFIRMED, OrderStatus.DELIVERED]),
                Order.created_at.between(start_date, end_date)
            ).scalar() or 0

            # 平均订单价值
            avg_order_value = total_sales / order_count if order_count > 0 else 0

            statistics = {
                'total_sales': float(total_sales),
                'order_count': order_count,
                'avg_order_value': float(avg_order_value),
                'period': {
                    'start': start_date,
                    'end': end_date
                }
            }

            logger.info(f"获取销售统计: {start_date} 到 {end_date}, 销售额: {total_sales}")
            return statistics
        except Exception as e:
            logger.error(f"获取销售统计失败: {str(e)}")
            return {}


class OrderItemRepository(BaseRepository[OrderItem]):
    """订单项数据访问层"""

    def __init__(self, db: Session):
        super().__init__(OrderItem, db)

    def get_order_items(self, order_id: int) -> List[OrderItem]:
        """获取订单的所有订单项"""
        try:
            items = self.db.query(OrderItem).options(
                joinedload(OrderItem.product)
            ).filter(OrderItem.order_id == order_id).all()

            logger.debug(f"获取订单 {order_id} 的订单项, 数量: {len(items)}")
            return items
        except Exception as e:
            logger.error(f"获取订单项失败: {str(e)}")
            return []


class PaymentRepository(BaseRepository[Payment]):
    """支付数据访问层"""

    def __init__(self, db: Session):
        super().__init__(Payment, db)

    def create_payment(self, payment_data: dict) -> Optional[Payment]:
        """创建支付记录"""
        try:
            return self.create(payment_data)
        except Exception as e:
            logger.error(f"创建支付记录失败: {str(e)}")
            return None

    def update_payment_status(self, payment_id: int, new_status: PaymentStatus,
                              gateway_transaction_id: str = None) -> bool:
        """更新支付状态"""
        try:
            payment = self.get_by_id(payment_id)
            if payment:
                payment.payment_status = new_status
                if gateway_transaction_id:
                    payment.gateway_transaction_id = gateway_transaction_id
                if new_status == PaymentStatus.PAID:
                    payment.payment_date = datetime.now()

                self.db.commit()
                logger.info(f"更新支付状态: {payment_id} -> {new_status}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新支付状态失败: {str(e)}")
            return False

    def get_payment_by_transaction(self, transaction_id: str) -> Optional[Payment]:
        """根据交易ID获取支付记录"""
        try:
            payment = self.db.query(Payment).options(
                joinedload(Payment.order)
            ).filter(Payment.transaction_id == transaction_id).first()

            logger.debug(f"根据交易ID查询支付: {transaction_id}")
            return payment
        except Exception as e:
            logger.error(f"查询支付记录失败: {str(e)}")
            return None