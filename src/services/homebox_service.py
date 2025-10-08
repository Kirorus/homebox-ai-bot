"""
HomeBox API service
"""

import aiohttp
import asyncio
import logging
from typing import List, Dict, Optional
from config.settings import HomeBoxSettings
from models.location import Location, LocationManager
from models.item import Item
from utils.retry import retry_async

logger = logging.getLogger(__name__)


class HomeBoxService:
    """Service for HomeBox API integration"""
    
    def __init__(self, settings: HomeBoxSettings):
        self.settings = settings
        self.base_url = settings.url
        self.token = settings.token
        self.username = settings.username
        self.password = settings.password
        self.last_error: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        self.headers = {
            'Authorization': self._build_auth_header(self.token),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _build_auth_header(self, token: Optional[str]) -> str:
        """Build authorization header"""
        if not token:
            return ''
        
        if token.startswith('Bearer '):
            return token
        else:
            return f'Bearer {token}'
    
    async def initialize(self):
        """Initialize the service"""
        await self._get_session()
        if not self.token and (self.username and self.password):
            await self._login()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
                )
            return self._session
    
    async def close(self):
        """Close HTTP session"""
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
    
    async def _login(self):
        """Login to HomeBox API"""
        try:
            session = await self._get_session()
            
            login_headers = {
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            payload = {
                'username': self.username,
                'password': self.password
            }
            
            logger.info("Attempting to login to HomeBox")
            
            async with session.post(
                f'{self.base_url}/api/v1/users/login',
                data=payload,
                headers=login_headers
            ) as response:
                if response.status != 200:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'LOGIN failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Login failed: {self.last_error}")
                    return
                
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError as e:
                    self.last_error = f'LOGIN response not JSON: {e}'
                    logger.error(self.last_error)
                    return
                
                token = data.get('token')
                if not token:
                    self.last_error = 'LOGIN response missing token'
                    logger.error(self.last_error)
                    return
                
                self.token = token
                self.headers['Authorization'] = self._build_auth_header(token)
                logger.info("Successfully logged in to HomeBox")
                
        except Exception as e:
            self.last_error = f'Exception during login: {str(e)}'
            logger.error(self.last_error)
    
    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def get_locations(self) -> List[Location]:
        """Fetch all locations from HomeBox"""
        try:
            session = await self._get_session()
            
            logger.info("Fetching locations from HomeBox")
            
            async with session.get(
                f'{self.base_url}/api/v1/locations',
                headers=self.headers
            ) as response:
                if response.status != 200:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'GET locations failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to fetch locations: {self.last_error}")
                    return []
                
                try:
                    locations_data = await response.json()
                    locations = [Location.from_dict(loc) for loc in locations_data]
                    logger.info(f"Successfully fetched {len(locations)} locations")
                    return locations
                except Exception as e:
                    self.last_error = f'Failed to parse locations: {e}'
                    logger.error(self.last_error)
                    return []
                    
        except Exception as e:
            error_msg = f'Exception in get_locations: {str(e)}'
            logger.error(error_msg)
            return []
    
    def get_location_manager(self, locations: List[Location]) -> LocationManager:
        """Create location manager with filtering"""
        # Filter locations based on settings
        filtered_locations = []
        for loc in locations:
            if loc.matches_filter(self.settings.location_filter_mode, self.settings.location_marker):
                loc.is_allowed = True
                filtered_locations.append(loc)
            else:
                loc.is_allowed = False
                filtered_locations.append(loc)
        
        return LocationManager(filtered_locations)
    
    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def create_item(self, item: Item) -> Dict:
        """Create a new item in HomeBox"""
        try:
            session = await self._get_session()
            
            logger.info(f"Creating item: {item.name} in location {item.location_id}")
            
            # Prepare item data
            item_data = item.to_homebox_format()
            
            async with session.post(
                f'{self.base_url}/api/v1/items',
                headers=self.headers,
                json=item_data
            ) as response:
                if response.status != 201:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'CREATE item failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to create item: {self.last_error}")
                    return {'error': f'Failed to create item: HTTP {response.status}'}
                
                try:
                    item_result = await response.json()
                except aiohttp.ContentTypeError as e:
                    self.last_error = f'CREATE item response not JSON: {e}'
                    logger.error(self.last_error)
                    return {'error': 'Failed to parse item response'}
                
                item_id = item_result.get('id')
                logger.info(f"Successfully created item with ID: {item_id}")
                
                # If there's a photo, upload it
                if item.photo_path and item_id:
                    logger.info(f"Uploading photo for item {item_id}")
                    uploaded = await self.upload_photo(item_id, item.photo_path)
                    if not uploaded:
                        item_result['photo_upload'] = 'failed'
                        logger.warning(f"Photo upload failed for item {item_id}: {self.last_error}")
                    else:
                        logger.info(f"Photo upload succeeded for item {item_id}")
                
                return item_result
                
        except Exception as e:
            error_msg = f'Exception in create_item: {str(e)}'
            logger.error(error_msg)
            return {'error': 'Exception occurred', 'details': str(e)}
    
    async def upload_photo(self, item_id: str, photo_path: str) -> bool:
        """Upload photo for an item"""
        try:
            import os
            import uuid
            
            # Read file
            with open(photo_path, 'rb') as file:
                file_content = file.read()
            
            filename = os.path.basename(photo_path) or 'photo.jpg'
            
            logger.info(f"Uploading photo {filename} for item {item_id}")
            
            # Create boundary
            boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
            
            # Form request body manually
            body_parts = []
            
            # Add name field (required by API)
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(f'Content-Disposition: form-data; name="name"'.encode())
            body_parts.append(b'')
            body_parts.append(filename.encode())
            
            # Add file
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
            body_parts.append(b'Content-Type: image/jpeg')
            body_parts.append(b'')
            body_parts.append(file_content)
            body_parts.append(f'--{boundary}--'.encode())
            
            body = b'\r\n'.join(body_parts)
            
            # Headers
            headers = {
                'Authorization': self._build_auth_header(self.token),
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Content-Length': str(len(body))
            }
            
            # Send via aiohttp
            session = await self._get_session()
            async with session.post(
                f'{self.base_url}/api/v1/items/{item_id}/attachments',
                headers=headers,
                data=body
            ) as response:
                logger.debug(f"Upload response status: {response.status}")
                
                if response.status != 201:
                    try:
                        body_text = await response.text()
                    except Exception:
                        body_text = ''
                    self.last_error = f'Upload failed HTTP {response.status}; body: {body_text[:500]}'
                    logger.error(f"Photo upload failed: {self.last_error}")
                    return False
                
                logger.info(f"Successfully uploaded photo for item {item_id}")
                return True
                
        except Exception as e:
            self.last_error = f'Exception in upload_photo: {str(e)}'
            logger.error(f"Exception in upload_photo: {e}")
            return False
    
    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def get_items(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get items from HomeBox"""
        try:
            session = await self._get_session()
            
            # Build query parameters according to HomeBox API
            params = {
                'pageSize': limit,
                'page': (offset // limit) + 1
            }
            
            logger.info(f"Fetching items from HomeBox (limit={limit}, offset={offset})")
            logger.info(f"Get items URL: {self.base_url}/api/v1/items")
            logger.info(f"Get items params: {params}")
            
            async with session.get(
                f'{self.base_url}/api/v1/items',
                headers=self.headers,
                params=params
            ) as response:
                logger.info(f"Get items response status: {response.status}")
                
                if response.status != 200:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'GET items failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to fetch items: {self.last_error}")
                    return []
                
                try:
                    response_data = await response.json()
                    logger.info(f"Get items API response type: {type(response_data)}")
                    
                    # Extract items from response
                    if isinstance(response_data, dict) and 'items' in response_data:
                        items_data = response_data['items']
                        logger.info(f"Successfully fetched {len(items_data)} items")
                        logger.info(f"Items response sample: {items_data[:2] if items_data else 'No items'}")
                        return items_data
                    elif isinstance(response_data, list):
                        # Direct array response
                        logger.info(f"Successfully fetched {len(response_data)} items")
                        logger.info(f"Items response sample: {response_data[:2] if response_data else 'No items'}")
                        return response_data
                    else:
                        logger.error(f"Unexpected response format: {type(response_data)}")
                        return []
                        
                except Exception as e:
                    self.last_error = f'Failed to parse items: {e}'
                    logger.error(self.last_error)
                    return []
                    
        except Exception as e:
            error_msg = f'Exception in get_items: {str(e)}'
            logger.error(error_msg)
            return []
    
    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def search_items(self, query: str, limit: int = 20) -> List[Dict]:
        """Search items by name or description using HomeBox API"""
        try:
            session = await self._get_session()
            
            # Build search parameters according to HomeBox API
            params = {
                'q': query,
                'pageSize': limit,
                'page': 1
            }
            
            logger.info(f"Searching items with query: '{query}'")
            logger.info(f"Search URL: {self.base_url}/api/v1/items")
            logger.info(f"Search params: {params}")
            
            async with session.get(
                f'{self.base_url}/api/v1/items',
                headers=self.headers,
                params=params
            ) as response:
                logger.info(f"Search response status: {response.status}")
                
                if response.status != 200:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'SEARCH items failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to search items: {self.last_error}")
                    return []
                
                try:
                    response_data = await response.json()
                    logger.info(f"Search API response type: {type(response_data)}")
                    
                    # Extract items from response
                    if isinstance(response_data, dict) and 'items' in response_data:
                        items_data = response_data['items']
                        logger.info(f"Found {len(items_data)} items for query: '{query}'")
                        logger.info(f"Search response sample: {items_data[:2] if items_data else 'No items'}")
                        return items_data
                    elif isinstance(response_data, list):
                        # Direct array response
                        logger.info(f"Found {len(response_data)} items for query: '{query}'")
                        logger.info(f"Search response sample: {response_data[:2] if response_data else 'No items'}")
                        return response_data
                    else:
                        logger.error(f"Unexpected response format: {type(response_data)}")
                        return []
                        
                except Exception as e:
                    self.last_error = f'Failed to parse search results: {e}'
                    logger.error(self.last_error)
                    return []
                    
        except Exception as e:
            error_msg = f'Exception in search_items: {str(e)}'
            logger.error(error_msg)
            return []
    
    async def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        """Get specific item by ID"""
        try:
            session = await self._get_session()
            
            logger.info(f"Fetching item {item_id} from HomeBox")
            
            async with session.get(
                f'{self.base_url}/api/v1/items/{item_id}',
                headers=self.headers
            ) as response:
                if response.status != 200:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'GET item {item_id} failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to fetch item {item_id}: {self.last_error}")
                    return None
                
                try:
                    item_data = await response.json()
                    logger.info(f"Successfully fetched item {item_id}")
                    return item_data
                except Exception as e:
                    self.last_error = f'Failed to parse item {item_id}: {e}'
                    logger.error(self.last_error)
                    return None
                    
        except Exception as e:
            error_msg = f'Exception in get_item_by_id: {str(e)}'
            logger.error(error_msg)
            return None
    
    async def get_image_url(self, image_id: str, item_id: str) -> str:
        """Get image URL from image ID and item ID"""
        if not image_id or not item_id:
            return ""
        
        # Get access token
        access_token = await self._get_access_token()
        if not access_token:
            logger.warning("No access token available for image URL")
            return ""
        
        # Format: /api/v1/items/{item_id}/attachments/{attachment_id}?access_token={token}
        return f"{self.base_url}/api/v1/items/{item_id}/attachments/{image_id}?access_token={access_token}"
    
    async def _get_access_token(self) -> str:
        """Get access token for API calls"""
        if self.token:
            # Remove 'Bearer ' prefix if present for URL parameter
            return self.token.replace('Bearer ', '')
        return ""
    