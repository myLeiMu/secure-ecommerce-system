from typing import List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc
from src.Data_base.models.product import Product, Category
from src.Data_base.repositories.base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)


class ProductRepository(BaseRepository[Product]):
    """商品数据访问层"""

    def __init__(self, db: Session):
        super().__init__(Product, db)

    def search_products_safe(self, keyword: str = None, category_id: int = None,
                             min_price: float = None, max_price: float = None,
                             in_stock: bool = True, skip: int = 0, limit: int = 50) -> List[Product]:
        """安全商品搜索（防SQL注入）"""
        try:
            query = self.db.query(Product).options(
                joinedload(Product.category)
            ).filter(
                Product.is_active == True,
                Product.is_available == True
            )

            # 关键字搜索（ORM转义防注入）
            if keyword:
                search_pattern = f"%{keyword}%"
                query = query.filter(
                    or_(
                        Product.product_name.like(search_pattern),
                        Product.description.like(search_pattern),
                        Product.sku.like(search_pattern)
                    )
                )

            # 分类过滤
            if category_id:
                query = query.filter(Product.category_id == category_id)

            # 价格范围过滤
            if min_price is not None:
                query = query.filter(Product.sale_price >= min_price)
            if max_price is not None:
                query = query.filter(Product.sale_price <= max_price)

            # 库存过滤
            if in_stock:
                query = query.filter(Product.stock_quantity > 0)

            products = query.order_by(desc(Product.created_at)).offset(skip).limit(limit).all()

            logger.info(f"商品搜索: keyword='{keyword}', category={category_id}, 结果数: {len(products)}")
            return products
        except Exception as e:
            logger.error(f"商品搜索失败: {str(e)}")
            return []

    def get_featured_products(self, limit: int = 10) -> List[Product]:
        """获取推荐商品"""
        try:
            products = self.db.query(Product).options(
                joinedload(Product.category)
            ).filter(
                Product.is_active == True,
                Product.is_available == True,
                Product.is_featured == True,
                Product.stock_quantity > 0
            ).order_by(desc(Product.created_at)).limit(limit).all()

            logger.debug(f"获取推荐商品, 数量: {len(products)}")
            return products
        except Exception as e:
            logger.error(f"获取推荐商品失败: {str(e)}")
            return []

    def update_stock(self, product_id: int, quantity: int) -> bool:
        """更新商品库存（事务安全）"""
        try:
            product = self.get_by_id(product_id)
            if product and product.track_inventory:
                if product.stock_quantity + quantity >= 0:  # 防止库存为负
                    product.stock_quantity += quantity
                    self.db.commit()
                    logger.info(f"更新商品 {product_id} 库存: 变化{quantity}, 新库存{product.stock_quantity}")
                    return True
                else:
                    logger.warning(f"商品 {product_id} 库存不足")
                    return False
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新商品库存失败: {str(e)}")
            return False

    def get_products_by_category(self, category_id: int, skip: int = 0, limit: int = 50) -> List[Product]:
        """根据分类获取商品"""
        try:
            products = self.db.query(Product).filter(
                Product.category_id == category_id,
                Product.is_active == True,
                Product.is_available == True
            ).order_by(desc(Product.created_at)).offset(skip).limit(limit).all()

            logger.debug(f"获取分类 {category_id} 的商品, 数量: {len(products)}")
            return products
        except Exception as e:
            logger.error(f"获取分类商品失败: {str(e)}")
            return []

    def get_low_stock_products(self, threshold: int = 10) -> List[Product]:
        """获取低库存商品"""
        try:
            products = self.db.query(Product).filter(
                Product.stock_quantity <= threshold,
                Product.track_inventory == True,
                Product.is_active == True
            ).order_by(Product.stock_quantity.asc()).all()

            logger.info(f"获取低库存商品(阈值{threshold}), 数量: {len(products)}")
            return products
        except Exception as e:
            logger.error(f"获取低库存商品失败: {str(e)}")
            return []


class CategoryRepository(BaseRepository[Category]):
    """商品分类数据访问层"""

    def __init__(self, db: Session):
        super().__init__(Category, db)

    def find_or_create_category(self, category_name: str, parent_id: int = None,
                                level: int = 1, sort_order: int = 1) -> Category:
        """查找或创建分类：如果存在同名分类就直接返回，否则创建新分类"""
        try:
            # 构建查询条件
            query_filters = [
                Category.category_name == category_name,
                Category.is_active == True
            ]

            # 如果有父分类ID，就按父分类查找；如果没有，就查找顶级分类
            if parent_id:
                query_filters.append(Category.parent_category_id == parent_id)
            else:
                query_filters.append(Category.parent_category_id.is_(None))

            # 查找现有分类
            existing_category = self.db.query(Category).filter(*query_filters).first()

            if existing_category:
                print(f" 使用现有分类: {category_name} (ID: {existing_category.category_id})")
                return existing_category

            # 创建新分类
            category_data = {
                'category_name': category_name,
                'parent_category_id': parent_id,
                'category_level': level,
                'sort_order': sort_order,
                'is_active': True
            }

            new_category = self.create(category_data)
            if new_category:
                print(f" 创建新分类: {category_name} (ID: {new_category.category_id})")
            else:
                print(f" 创建分类失败: {category_name}")

            return new_category

        except Exception as e:
            logger.error(f"查找或创建分类失败: {str(e)}")
            return None

    def get_categories_tree(self) -> List[Category]:
        """获取分类树结构"""
        try:
            # 获取所有顶级分类
            top_categories = self.db.query(Category).filter(
                Category.parent_category_id.is_(None),
                Category.is_active == True
            ).order_by(Category.sort_order).all()

            logger.debug(f"获取分类树, 顶级分类数: {len(top_categories)}")
            return top_categories
        except Exception as e:
            logger.error(f"获取分类树失败: {str(e)}")
            return []

    def get_subcategories(self, parent_id: int) -> List[Category]:
        """获取子分类"""
        try:
            subcategories = self.db.query(Category).filter(
                Category.parent_category_id == parent_id,
                Category.is_active == True
            ).order_by(Category.sort_order).all()

            logger.debug(f"获取父分类 {parent_id} 的子分类, 数量: {len(subcategories)}")
            return subcategories
        except Exception as e:
            logger.error(f"获取子分类失败: {str(e)}")
            return []