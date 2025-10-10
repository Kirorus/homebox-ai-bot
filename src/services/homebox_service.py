"""
HomeBox API service
"""

import aiohttp
import asyncio
import logging
from typing import List, Dict, Optional, Any
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
        # Runtime token obtained via login; not from static settings
        self.token: Optional[str] = None
        self.username = settings.username
        self.password = settings.password
        self.last_error: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        # Headers will include Authorization after successful login
        self.headers = {
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
        # Only perform login when no token is currently available
        if self.token is None and self.username and self.password:
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
    async def create_location(self, name: str, description: Optional[str] = None, parent_id: Optional[str] = None) -> Optional[Location]:
        """Create a new location in HomeBox.
        Only include optional fields when provided to avoid unintended defaults server-side.
        """
        try:
            session = await self._get_session()
            logger.info(f"Creating location: name='{name}', parent={parent_id}")
            if not name or not name.strip():
                self.last_error = 'Location name is required'
                logger.error(self.last_error)
                return None
            payload: Dict[str, Any] = { 'name': name.strip() }
            if description is not None and description.strip():
                payload['description'] = description.strip()
            if parent_id:
                payload['parentId'] = parent_id
            async with session.post(
                f"{self.base_url}/api/v1/locations",
                headers=self.headers,
                json=payload
            ) as response:
                if response.status not in [200, 201]:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f"CREATE location failed HTTP {response.status}; body: {body[:500]}"
                    logger.error(f"Failed to create location: {self.last_error}")
                    return None
                try:
                    data = await response.json()
                    location = Location.from_dict(data)
                    logger.info(f"Successfully created location with ID: {location.id}")
                    return location
                except Exception as e:
                    self.last_error = f"Failed to parse created location: {e}"
                    logger.error(self.last_error)
                    return None
        except Exception as e:
            error_msg = f"Exception in create_location: {str(e)}"
            logger.error(error_msg)
            return None
    
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

    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def delete_item(self, item_id: str) -> bool:
        """Delete item by ID in HomeBox"""
        try:
            session = await self._get_session()
            logger.info(f"Deleting item {item_id} from HomeBox")
            async with session.delete(
                f'{self.base_url}/api/v1/items/{item_id}',
                headers=self.headers
            ) as response:
                if response.status not in [200, 204]:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'DELETE item failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to delete item {item_id}: {self.last_error}")
                    return False
                logger.info(f"Successfully deleted item {item_id}")
                return True
        except Exception as e:
            error_msg = f'Exception in delete_item: {str(e)}'
            logger.error(error_msg)
            return False
    
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
    
    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def update_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Update item fields in HomeBox"""
        try:
            session = await self._get_session()
            
            logger.info(f"Updating item {item_id} with fields: {list(updates.keys())}")
            
            # First get the current item to preserve other fields
            current_item = await self.get_item_by_id(item_id)
            if not current_item:
                self.last_error = f"Item {item_id} not found"
                logger.error(self.last_error)
                return False
            
            # Prepare update data - merge current data with updates
            update_data = {
                'name': current_item.get('name', ''),
                'description': current_item.get('description', ''),
                'locationId': current_item.get('location', {}).get('id', '') if isinstance(current_item.get('location'), dict) else current_item.get('locationId', ''),
                'quantity': current_item.get('quantity', 1)
            }
            
            # Apply updates
            for key, value in updates.items():
                if key == 'location_id':
                    update_data['locationId'] = value
                elif key in ['name', 'description', 'quantity']:
                    update_data[key] = value
            
            async with session.put(
                f'{self.base_url}/api/v1/items/{item_id}',
                headers=self.headers,
                json=update_data
            ) as response:
                if response.status not in [200, 204]:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'UPDATE item failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to update item: {self.last_error}")
                    return False
                
                logger.info(f"Successfully updated item {item_id}")
                return True
                
        except Exception as e:
            error_msg = f'Exception in update_item: {str(e)}'
            logger.error(error_msg)
            return False
    
    async def update_item_location(self, item_id: str, new_location_id: str) -> bool:
        """Update item location in HomeBox"""
        return await self.update_item(item_id, {'location_id': new_location_id})
    
    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def update_location(self, location_id: str, updates: Dict[str, Any]) -> bool:
        """Update location fields in HomeBox"""
        try:
            session = await self._get_session()
            
            logger.info(f"Updating location {location_id} with fields: {list(updates.keys())}")
            
            # First get the current location to preserve other fields
            current_location = await self.get_location_by_id(location_id)
            if not current_location:
                self.last_error = f"Location {location_id} not found"
                logger.error(self.last_error)
                return False
            
            # Prepare update data - merge current data with updates
            # IMPORTANT: do NOT include parentId if it's empty/None, to avoid resetting parent on the server
            update_data = {
                'name': current_location.name,
                'description': current_location.description or ''
            }
            if current_location.parent_id:
                update_data['parentId'] = current_location.parent_id
            
            # Apply updates
            for key, value in updates.items():
                if key == 'description':
                    update_data['description'] = value
                elif key == 'name':
                    update_data['name'] = value
                elif key == 'parent_id':
                    # Only include if explicitly provided (used to change parent)
                    update_data['parentId'] = value
            
            async with session.put(
                f'{self.base_url}/api/v1/locations/{location_id}',
                headers=self.headers,
                json=update_data
            ) as response:
                if response.status not in [200, 204]:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'UPDATE location failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to update location: {self.last_error}")
                    return False
                
                logger.info(f"Successfully updated location {location_id}")
                return True
                
        except Exception as e:
            error_msg = f'Exception in update_location: {str(e)}'
            logger.error(error_msg)
            return False
    
    async def get_location_by_id(self, location_id: str) -> Optional[Location]:
        """Get specific location by ID"""
        try:
            session = await self._get_session()
            
            logger.info(f"Fetching location {location_id} from HomeBox")
            
            async with session.get(
                f'{self.base_url}/api/v1/locations/{location_id}',
                headers=self.headers
            ) as response:
                if response.status != 200:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'GET location {location_id} failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to fetch location {location_id}: {self.last_error}")
                    return None
                
                try:
                    location_data = await response.json()
                    location = Location.from_dict(location_data)
                    logger.info(f"Successfully fetched location {location_id}")
                    return location
                except Exception as e:
                    self.last_error = f'Failed to parse location {location_id}: {e}'
                    logger.error(self.last_error)
                    return None
                    
        except Exception as e:
            error_msg = f'Exception in get_location_by_id: {str(e)}'
            logger.error(error_msg)
            return None
    
    async def download_item_image(self, item_id: str, image_id: str) -> Optional[str]:
        """Download item image and save to temporary file"""
        try:
            import aiofiles
            import os
            import tempfile
            
            if not image_id or not item_id:
                return None
            
            # Get access token
            access_token = await self._get_access_token()
            if not access_token:
                logger.warning("No access token available for image download")
                return None
            
            # Build image URL
            image_url = f"{self.base_url}/api/v1/items/{item_id}/attachments/{image_id}?access_token={access_token}"
            
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            temp_filename = f"reanalysis_{item_id}_{image_id}.jpg"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            logger.info(f"Downloading image for reanalysis: {image_url}")
            
            # Download image
            session = await self._get_session()
            async with session.get(image_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download image: HTTP {response.status}")
                    return None
                
                # Save to temporary file
                async with aiofiles.open(temp_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
            
            logger.info(f"Image downloaded successfully: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Exception in download_item_image: {str(e)}")
            return None
    
    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def get_items_by_location(self, location_id: str) -> List[Dict]:
        """Get items from specific location"""
        try:
            session = await self._get_session()
            
            logger.info(f"Fetching items from location {location_id}")
            
            # Get all items and filter by location
            all_items = []
            page = 1
            page_size = 50
            
            while True:
                params = {
                    'pageSize': page_size,
                    'page': page
                }
                
                async with session.get(
                    f'{self.base_url}/api/v1/items',
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        try:
                            body = await response.text()
                        except Exception:
                            body = ''
                        self.last_error = f'GET items failed HTTP {response.status}; body: {body[:500]}'
                        logger.error(f"Failed to fetch items: {self.last_error}")
                        return []
                    
                    try:
                        data = await response.json()
                        # Support multiple API response shapes
                        if isinstance(data, dict):
                            items_data = data.get('items') or data.get('data') or []
                        elif isinstance(data, list):
                            items_data = data
                        else:
                            items_data = []

                        if not items_data:
                            break

                        # Filter items by location (support both 'locationId' and nested 'location.id')
                        def extract_loc_id(d: Dict[str, Any]) -> str:
                            loc = d.get('location')
                            if isinstance(loc, dict) and 'id' in loc:
                                return str(loc.get('id'))
                            return str(d.get('locationId', ''))

                        location_items = [
                            item_data for item_data in items_data
                            if extract_loc_id(item_data) == str(location_id)
                        ]
                        all_items.extend(location_items)

                        # Check if there are more pages
                        if len(items_data) < page_size:
                            break

                        page += 1

                    except Exception as e:
                        logger.error(f"Failed to parse items data: {e}")
                        break
            
            logger.info(f"Successfully fetched {len(all_items)} items from location {location_id}")
            return all_items
                
        except Exception as e:
            error_msg = f'Exception in get_items_by_location: {str(e)}'
            logger.error(error_msg)
            return []
    
    async def _get_access_token(self) -> str:
        """Get access token for API calls"""
        if self.token:
            # Remove 'Bearer ' prefix if present for URL parameter
            return self.token.replace('Bearer ', '')
        return ""
    