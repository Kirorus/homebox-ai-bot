import aiohttp
from typing import List, Dict, Optional
import config

class HomeboxAPI:
    def __init__(self):
        # Normalize base URL (strip trailing slash)
        self.base_url = (config.HOMEBOX_URL or "").rstrip("/")
        self.token = config.HOMEBOX_TOKEN
        self.username = config.HOMEBOX_USER
        self.password = config.HOMEBOX_PASSWORD
        self.last_error: Optional[str] = None
        self.headers = {
            'Authorization': self._build_auth_header(self.token),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _build_auth_header(self, token: Optional[str]) -> str:
        """Собирает значение заголовка Authorization.
        Некоторые инсталляции Homebox ожидают чистый токен без префикса Bearer.
        Если в токене уже есть префикс 'Bearer ', используем как есть; иначе — передаём токен как есть без префикса.
        """
        if not token:
            return ''
        if isinstance(token, str) and token.strip().lower().startswith('bearer '):
            return token
        return token
    
    async def get_locations(self) -> List[Dict]:
        """Fetch all locations (boxes)."""
        await self.ensure_authorized()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{self.base_url}/api/v1/locations',
                headers=self.headers
            ) as response:
                if response.status != 200:
                    # Try read error body for diagnostics
                    try:
                        error_text = await response.text()
                    except Exception:
                        error_text = ''
                    self.last_error = f'GET /api/v1/locations -> HTTP {response.status}; body: {error_text[:500]}'
                    return []
                # Safe JSON parse: proxies/redirects may return HTML
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError:
                    self.last_error = 'GET /api/v1/locations -> invalid content-type (expected JSON)'
                    return []
                # Support both array response and object { items: [] }
                locations: List[Dict] = []
                if isinstance(data, list):
                    locations = data
                elif isinstance(data, dict):
                    items = data.get('items')
                    if isinstance(items, list):
                        locations = items
                self.last_error = None
                return locations
    
    async def create_item(
        self,
        name: str,
        description: str,
        location_id: str,
        photo_path: Optional[str] = None
    ) -> Dict:
        """Create a new item in HomeBox."""
        # Сначала создаем предмет
        await self.ensure_authorized()
        item_data = {
            'name': name,
            'description': description,
            'locationId': location_id,
            'quantity': 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/api/v1/items',
                headers=self.headers,
                json=item_data
            ) as response:
                if response.status != 201:
                    try:
                        error_text = await response.text()
                    except Exception:
                        error_text = ''
                    return {'error': 'Failed to create item', 'details': error_text}

                try:
                    item = await response.json()
                except aiohttp.ContentTypeError:
                    return {'error': 'Failed to parse item response'}
                item_id = item.get('id')
                
                # Если есть фото, загружаем его
                if photo_path and item_id:
                    uploaded = await self.upload_photo(item_id, photo_path)
                    if not uploaded:
                        # Вернём флаг/сообщение, чтобы бот мог показать пользователю
                        item['photo_upload'] = 'failed'
                
                return item
    
    async def upload_photo(self, item_id: str, photo_path: str) -> bool:
        """Upload a photo for the given item."""
        async with aiohttp.ClientSession() as session:
            with open(photo_path, 'rb') as file:
                data = aiohttp.FormData()
                # Имя требуется API: добавим поле 'name' и корректное имя файла
                import os as _os
                filename = _os.path.basename(photo_path) or 'photo.jpg'
                data.add_field('name', filename)
                data.add_field('file', file, filename=filename, content_type='image/jpeg')
                
                async with session.post(
                    f'{self.base_url}/api/v1/items/{item_id}/attachments',
                    headers={'Authorization': self._build_auth_header(self.token)},
                    data=data
                ) as response:
                    if response.status != 201:
                        try:
                            body = await response.text()
                        except Exception:
                            body = ''
                        self.last_error = f'UPLOAD photo failed HTTP {response.status}; body: {body[:500]}'
                        return False
                    return True

    async def ensure_authorized(self) -> None:
        """Ensure we have a valid token; if absent, perform login."""
        if self.token:
            # Токен уже есть
            return
        # Require username/password for login
        if not self.username or not self.password:
            self.last_error = 'No HOMEBOX_TOKEN and no HOMEBOX_USER/HOMEBOX_PASSWORD provided'
            return
        # Perform login
        login_headers = {
            'accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        payload = {
            'username': self.username,
            'password': self.password
        }
        async with aiohttp.ClientSession() as session:
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
                    return
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError:
                    self.last_error = 'LOGIN response not JSON'
                    return
                token = data.get('token')
                if not token:
                    self.last_error = 'LOGIN response missing token'
                    return
                # В некоторых установках нужен чистый токен без Bearer — используем стратегию _build_auth_header
                self.token = token
                self.headers['Authorization'] = self._build_auth_header(self.token)
                self.last_error = None
