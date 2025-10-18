import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class CartServiceClient:
    def __init__(self, base_url: str = "http://cart_service:8000"):
        self.base_url = base_url
        self.timeout = 10.0
    
    async def get_cart_by_user(self, user_id: int) -> Optional[Dict[Any, Any]]:
        """Get cart items for a user via HTTP"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/shopcarts/user/{user_id}")
                
                if response.status_code == 404:
                    logger.warning(f"Cart not found for user_id: {user_id}")
                    return None
                
                response.raise_for_status()
                cart_data = response.json()
                
                logger.info(f"✅ Retrieved cart for user_id: {user_id}")
                return cart_data
                
        except httpx.HTTPStatusError as e:
            logger.error(f" HTTP error getting cart: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f" Request error getting cart: {e}")
            raise
        except Exception as e:
            logger.error(f" Unexpected error getting cart: {e}")
            raise