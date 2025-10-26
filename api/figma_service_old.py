"""
Figma API integration service for fetching and converting design data.
"""
import os
import requests
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re

@dataclass
class FigmaComponent:
    """Represents a Figma component with its styling data."""
    id: str
    name: str
    type: str
    styles: Dict[str, Any]
    svg_data: Optional[str] = None
    bounds: Optional[Dict[str, float]] = None

class FigmaService:
    """Service for interacting with Figma REST API."""
    
    def __init__(self):
        self.api_token = os.getenv('FIGMA_API_TOKEN')
        self.file_id = os.getenv('FIGMA_FILE_ID')
        self.base_url = 'https://api.figma.com/v1'
        self.headers = {
            'X-Figma-Token': self.api_token,
            'Content-Type': 'application/json'
        }
        
        if not self.api_token:
            raise ValueError("FIGMA_API_TOKEN environment variable is required")
        if not self.file_id:
            raise ValueError("FIGMA_FILE_ID environment variable is required")
    
    def fetch_file_data(self) -> Dict[str, Any]:
        """Fetch the complete Figma file data."""
        url = f"{self.base_url}/files/{self.file_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch Figma file: {str(e)}")
    
    def fetch_components(self) -> List[FigmaComponent]:
        """Fetch and parse components from the Figma file."""
        file_data = self.fetch_file_data()
        components = []
        
        # Extract components from the file structure
        def traverse_nodes(nodes: List[Dict], parent_name: str = ""):
            for node in nodes:
                node_name = node.get('name', '')
                full_name = f"{parent_name}/{node_name}" if parent_name else node_name
                
                # Check if this is a component we're interested in
                if self._is_overlay_component(node_name):
                    component = self._parse_component(node, full_name)
                    if component:
                        components.append(component)
                
                # Recursively traverse children
                if 'children' in node:
                    traverse_nodes(node['children'], full_name)
        
        # Start traversal from document children
        if 'document' in file_data and 'children' in file_data['document']:
            traverse_nodes(file_data['document']['children'])
        
        return components
    
    def fetch_component_svg(self, component_id: str) -> Optional[str]:
        """Fetch SVG data for a specific component."""
        url = f"{self.base_url}/images/{self.file_id}"
        params = {
            'ids': component_id,
            'format': 'svg'
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'images' in data and component_id in data['images']:
                svg_url = data['images'][component_id]
                if svg_url:
                    svg_response = requests.get(svg_url)
                    svg_response.raise_for_status()
                    return svg_response.text
            
            return None
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch SVG for component {component_id}: {str(e)}")
            return None
    
    def _is_overlay_component(self, name: str) -> bool:
        """Check if a component name matches our overlay naming conventions."""
        overlay_keywords = [
            'bounding-box', 'bbox', 'box',
            'crosshair', 'reticle', 'target',
            'text-label', 'label', 'text',
            'tracking-dot', 'dot', 'marker',
            'status', 'indicator'
        ]
        
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in overlay_keywords)
    
    def _parse_component(self, node: Dict, full_name: str) -> Optional[FigmaComponent]:
        """Parse a Figma node into a FigmaComponent."""
        try:
            component_id = node.get('id')
            if not component_id:
                return None
            
            # Extract styling information
            styles = self._extract_styles(node)
            
            # Extract bounds
            bounds = None
            if 'absoluteBoundingBox' in node:
                bounds = node['absoluteBoundingBox']
            
            # Determine component type based on name
            component_type = self._determine_component_type(full_name)
            
            return FigmaComponent(
                id=component_id,
                name=full_name,
                type=component_type,
                styles=styles,
                bounds=bounds
            )
        except Exception as e:
            print(f"Failed to parse component {full_name}: {str(e)}")
            return None
    
    def _extract_styles(self, node: Dict) -> Dict[str, Any]:
        """Extract styling information from a Figma node."""
        styles = {}
        
        # Extract fills (background colors)
        if 'fills' in node and node['fills']:
            fill = node['fills'][0]  # Take first fill
            if fill.get('type') == 'SOLID' and 'color' in fill:
                color = fill['color']
                styles['color'] = self._rgba_to_hex(color)
                styles['opacity'] = color.get('a', 1.0)
                # Store backgroundColor as RGBA string to preserve opacity
                styles['backgroundColor'] = self._rgba_to_rgba_string(color)
                styles['backgroundOpacity'] = color.get('a', 1.0)
        
        # Extract strokes (border colors)
        if 'strokes' in node and node['strokes']:
            stroke = node['strokes'][0]
            if stroke.get('type') == 'SOLID' and 'color' in stroke:
                color = stroke['color']
                styles['borderColor'] = self._rgba_to_hex(color)
                styles['borderOpacity'] = color.get('a', 1.0)
        
        # Extract stroke weight
        if 'strokeWeight' in node:
            styles['borderWidth'] = node['strokeWeight']
        
        # Extract corner radius
        if 'cornerRadius' in node:
            styles['borderRadius'] = node['cornerRadius']
        
        # Extract text styles
        if node.get('type') == 'TEXT' and 'style' in node:
            text_style = node['style']
            if 'fontSize' in text_style:
                styles['fontSize'] = text_style['fontSize']
            if 'fontFamily' in text_style:
                styles['fontFamily'] = text_style['fontFamily']
            if 'fontWeight' in text_style:
                styles['fontWeight'] = text_style['fontWeight']
        
        # Extract effects (shadows, etc.)
        if 'effects' in node and node['effects']:
            for effect in node['effects']:
                if effect.get('type') == 'DROP_SHADOW':
                    styles['boxShadow'] = self._parse_shadow(effect)
        
        return styles
    
    def _rgba_to_hex(self, color: Dict) -> str:
        """Convert Figma RGBA color to hex string."""
        r = int(color.get('r', 0) * 255)
        g = int(color.get('g', 0) * 255)
        b = int(color.get('b', 0) * 255)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _rgba_to_rgba_string(self, color: Dict[str, float]) -> str:
        """Convert RGBA color to rgba() string format."""
        r = int(color.get('r', 0) * 255)
        g = int(color.get('g', 0) * 255)
        b = int(color.get('b', 0) * 255)
        a = color.get('a', 1.0)
        return f"rgba({r}, {g}, {b}, {a})"
    
    def _parse_shadow(self, effect: Dict) -> str:
        """Parse Figma shadow effect to CSS box-shadow."""
        offset = effect.get('offset', {})
        x = offset.get('x', 0)
        y = offset.get('y', 0)
        blur = effect.get('radius', 0)
        
        color = effect.get('color', {})
        color_hex = self._rgba_to_hex(color)
        opacity = color.get('a', 1.0)
        
        return f"{x}px {y}px {blur}px rgba({int(color.get('r', 0) * 255)}, {int(color.get('g', 0) * 255)}, {int(color.get('b', 0) * 255)}, {opacity})"
    
    def _determine_component_type(self, name: str) -> str:
        """Determine the overlay component type from the name."""
        name_lower = name.lower()
        
        if any(keyword in name_lower for keyword in ['bounding-box', 'bbox', 'box']):
            if 'person' in name_lower:
                return 'person-box'
            elif 'vehicle' in name_lower:
                return 'vehicle-box'
            else:
                return 'bounding-box'
        elif any(keyword in name_lower for keyword in ['crosshair', 'reticle', 'target']):
            return 'crosshair'
        elif any(keyword in name_lower for keyword in ['text-label', 'label', 'text']):
            return 'text-label'
        elif any(keyword in name_lower for keyword in ['tracking-dot', 'dot', 'marker']):
            return 'tracking-dot'
        elif any(keyword in name_lower for keyword in ['status', 'indicator']):
            return 'status-indicator'
        else:
            return 'unknown'
    
    def convert_to_visual_settings(self, components: List[FigmaComponent]) -> Dict[str, Any]:
        """Convert Figma components to visual settings format with enhanced mapping."""
        settings = {}
        
        for component in components:
            styles = component.styles
            component_type = component.type
            name_lower = component.name.lower()
            
            # Enhanced mapping with more specific component detection
            if component_type == 'person-box' or 'person' in name_lower:
                # Map person bounding box styles based on state keywords
                # Check unlocked BEFORE locked to avoid matching "unlocked" as "locked"
                if any(keyword in name_lower for keyword in ['unlocked', 'default', 'normal']) or name_lower.endswith('unlocked'):
                    # Map all properties for unlocked person box
                    if styles.get('borderColor'):
                        settings['personUnlockedBoxColor'] = styles['borderColor']
                    elif styles.get('color'):
                        settings['personUnlockedBoxColor'] = styles['color']
                    if styles.get('backgroundColor'):
                        settings['personUnlockedBoxBackgroundColor'] = styles['backgroundColor']
                        settings['personUnlockedBoxBackgroundOpacity'] = styles.get('backgroundOpacity', 0.2)
                    if 'borderRadius' in styles:
                        settings['personUnlockedBoxBorderRadius'] = styles['borderRadius']
                    if 'borderWidth' in styles:
                        settings['personUnlockedBoxStrokeWidth'] = int(styles['borderWidth'])
                    
                    # Map text properties
                    if styles.get('personIdTextColor'):
                        settings['personIdTextColor'] = styles['personIdTextColor']
                    if styles.get('personIdTextSize'):
                        settings['personIdTextSize'] = styles['personIdTextSize']
                    if styles.get('personIdTextFamily'):
                        settings['personIdTextFamily'] = styles['personIdTextFamily']
                    if styles.get('personIdTextWeight'):
                        settings['personIdTextWeight'] = styles['personIdTextWeight']
                    
                elif any(keyword in name_lower for keyword in ['locked', 'targeted', 'active']):
                    # Map all properties for locked person box
                    if styles.get('borderColor'):
                        settings['personLockedBoxColor'] = styles['borderColor']
                    elif styles.get('color'):
                        settings['personLockedBoxColor'] = styles['color']
                    if styles.get('backgroundColor'):
                        settings['personLockedBoxBackgroundColor'] = styles['backgroundColor']
                        settings['personLockedBoxBackgroundOpacity'] = styles.get('backgroundOpacity', 0.2)
                    if 'borderRadius' in styles:
                        settings['personLockedBoxBorderRadius'] = styles['borderRadius']
                    if 'borderWidth' in styles:
                        settings['personLockedBoxStrokeWidth'] = int(styles['borderWidth'])
                    
                    # Map text properties for locked state
                    if styles.get('personIdTextColor'):
                        settings['personIdLockedTextColor'] = styles['personIdTextColor']
                    if styles.get('personIdTextSize'):
                        settings['personIdLockedTextSize'] = styles['personIdTextSize']
                    if styles.get('personIdTextFamily'):
                        settings['personIdLockedTextFamily'] = styles['personIdTextFamily']
                    if styles.get('personIdTextWeight'):
                        settings['personIdLockedTextWeight'] = styles['personIdTextWeight']
                    
                elif any(keyword in name_lower for keyword in ['far', 'distant', 'red']):
                    # Map all properties for far person box
                    if styles.get('borderColor'):
                        settings['personFarBoxColor'] = styles['borderColor']
                    elif styles.get('color'):
                        settings['personFarBoxColor'] = styles['color']
                    if styles.get('backgroundColor'):
                        settings['personFarBoxBackgroundColor'] = styles['backgroundColor']
                        settings['personFarBoxBackgroundOpacity'] = styles.get('backgroundOpacity', 0.2)
                    if 'borderRadius' in styles:
                        settings['personFarBoxBorderRadius'] = styles['borderRadius']
                    if 'borderWidth' in styles:
                        settings['personFarBoxStrokeWidth'] = int(styles['borderWidth'])
                    
                elif any(keyword in name_lower for keyword in ['grey', 'gray', 'background', 'inactive']):
                    # Map all properties for grey person box
                    if styles.get('borderColor'):
                        settings['personGreyColor'] = styles['borderColor']
                    elif styles.get('color'):
                        settings['personGreyColor'] = styles['color']
                    if styles.get('backgroundColor'):
                        settings['personGreyBackgroundColor'] = styles['backgroundColor']
                        settings['personGreyBackgroundOpacity'] = styles.get('backgroundOpacity', 0.2)
                    if 'borderRadius' in styles:
                        settings['personGreyBorderRadius'] = styles['borderRadius']
                    if 'borderWidth' in styles:
                        settings['personGreyStrokeWidth'] = int(styles['borderWidth'])
                
                # Map shared text properties (distance, object type)
                if styles.get('distanceTextColor'):
                    settings['distanceTextColor'] = styles['distanceTextColor']
                if styles.get('distanceTextSize'):
                    settings['distanceTextSize'] = styles['distanceTextSize']
                if styles.get('distanceTextFamily'):
                    settings['distanceTextFamily'] = styles['distanceTextFamily']
                if styles.get('distanceTextWeight'):
                    settings['distanceTextWeight'] = styles['distanceTextWeight']
                
                if styles.get('objectTypeTextColor'):
                    settings['objectTypeTextColor'] = styles['objectTypeTextColor']
                if styles.get('objectTypeTextSize'):
                    settings['objectTypeTextSize'] = styles['objectTypeTextSize']
                if styles.get('objectTypeTextFamily'):
                    settings['objectTypeTextFamily'] = styles['objectTypeTextFamily']
                if styles.get('objectTypeTextWeight'):
                    settings['objectTypeTextWeight'] = styles['objectTypeTextWeight']
                
                # Always try to map stroke width for any person box
                if 'borderWidth' in styles:
                    settings['personBoxStrokeWidth'] = int(styles['borderWidth'])
                
                # Handle grey/background state
                if any(keyword in name_lower for keyword in ['grey', 'gray', 'background', 'inactive']):
                    if styles.get('color'):
                        settings['personGreyColor'] = styles['color']
            
            elif component_type == 'vehicle-box' or 'vehicle' in name_lower:
                # Map vehicle bounding box styles
                if any(keyword in name_lower for keyword in ['locked', 'targeted', 'active']):
                    if styles.get('borderColor'):
                        settings['vehicleLockedBoxColor'] = styles['borderColor']
                    if styles.get('color') and not styles.get('borderColor'):
                        settings['vehicleLockedBoxColor'] = styles['color']
                elif any(keyword in name_lower for keyword in ['far', 'distant', 'orange']):
                    if styles.get('borderColor'):
                        settings['vehicleFarBoxColor'] = styles['borderColor']
                    if styles.get('color') and not styles.get('borderColor'):
                        settings['vehicleFarBoxColor'] = styles['color']
                elif any(keyword in name_lower for keyword in ['unlocked', 'default', 'normal']):
                    if styles.get('borderColor'):
                        settings['vehicleUnlockedBoxColor'] = styles['borderColor']
                    if styles.get('color') and not styles.get('borderColor'):
                        settings['vehicleUnlockedBoxColor'] = styles['color']
                
                if 'borderWidth' in styles:
                    settings['vehicleBoxStrokeWidth'] = int(styles['borderWidth'])
                
                # Handle grey/background state
                if any(keyword in name_lower for keyword in ['grey', 'gray', 'background', 'inactive']):
                    if styles.get('color'):
                        settings['vehicleGreyColor'] = styles['color']
            
            elif component_type == 'crosshair' or any(keyword in name_lower for keyword in ['crosshair', 'reticle', 'target']):
                if styles.get('borderColor'):
                    settings['crosshairColor'] = styles['borderColor']
                elif styles.get('color'):
                    settings['crosshairColor'] = styles['color']
                
                if 'borderWidth' in styles:
                    settings['crosshairWidth'] = int(styles['borderWidth'])
                
                # Determine crosshair size from bounds
                if component.bounds:
                    size = max(component.bounds.get('width', 20), component.bounds.get('height', 20))
                    settings['crosshairSize'] = int(size)
                
                # Store SVG data for custom crosshair
                if component.svg_data:
                    settings['customCrosshairImage'] = f"data:image/svg+xml;base64,{component.svg_data}"
                    settings['crosshairStyle'] = 'custom'
                elif 'circle' in name_lower:
                    settings['crosshairStyle'] = 'circle'
                elif 'cross' in name_lower:
                    settings['crosshairStyle'] = 'cross'
                else:
                    settings['crosshairStyle'] = 'lines'
            
            elif component_type == 'text-label' or any(keyword in name_lower for keyword in ['text', 'label']):
                if 'fontSize' in styles:
                    settings['textSize'] = int(styles['fontSize'])
                
                if styles.get('color'):
                    # Map text colors based on component name
                    if any(keyword in name_lower for keyword in ['person', 'people']) and 'locked' in name_lower:
                        settings['personIdLockedTextColor'] = styles['color']
                    elif any(keyword in name_lower for keyword in ['person', 'people']):
                        settings['personIdTextColor'] = styles['color']
                    elif any(keyword in name_lower for keyword in ['vehicle', 'car']) and 'locked' in name_lower:
                        settings['vehicleIdLockedTextColor'] = styles['color']
                    elif any(keyword in name_lower for keyword in ['vehicle', 'car']):
                        settings['vehicleIdTextColor'] = styles['color']
                    elif any(keyword in name_lower for keyword in ['distance', 'range']):
                        settings['distanceTextColor'] = styles['color']
                    elif any(keyword in name_lower for keyword in ['object', 'type']):
                        settings['objectTypeTextColor'] = styles['color']
                
                # Handle text background opacity
                if 'opacity' in styles:
                    settings['textBackgroundOpacity'] = styles['opacity']
            
            elif component_type == 'tracking-dot' or any(keyword in name_lower for keyword in ['dot', 'marker', 'tracking']):
                if styles.get('color'):
                    settings['trackingDotColor'] = styles['color']
                
                if component.bounds:
                    # Use component size as dot size
                    size = min(component.bounds.get('width', 6), component.bounds.get('height', 6))
                    settings['trackingDotSize'] = max(3, int(size / 2))
                
                # Store SVG data for custom tracking dot
                if component.svg_data:
                    settings['customTrackingImage'] = f"data:image/svg+xml;base64,{component.svg_data}"
                    settings['trackingDotStyle'] = 'custom'
                elif 'ring' in name_lower:
                    settings['trackingDotStyle'] = 'ring'
                elif 'cross' in name_lower:
                    settings['trackingDotStyle'] = 'cross'
                else:
                    settings['trackingDotStyle'] = 'solid'
            
            # Handle general box styling
            if any(keyword in name_lower for keyword in ['box', 'bounding']):
                if 'dashed' in name_lower or 'dash' in name_lower:
                    settings['boxStyle'] = 'dashed'
                else:
                    settings['boxStyle'] = 'solid'
            
            # Handle mode-specific settings
            if any(keyword in name_lower for keyword in ['taser', 'officer']):
                settings['enableCrosshair'] = True
                settings['showStatusSquare'] = False
            elif any(keyword in name_lower for keyword in ['hawkeye', 'dash']):
                settings['enableCrosshair'] = False
                settings['showStatusSquare'] = True
            elif 'all' in name_lower:
                settings['enableCrosshair'] = True
                settings['showStatusSquare'] = False
        
        return settings

# Global service instance
figma_service = None

def get_figma_service() -> FigmaService:
    """Get or create the global Figma service instance."""
    global figma_service
    if figma_service is None:
        try:
            figma_service = FigmaService()
        except ValueError as e:
            print(f"Figma service initialization failed: {e}")
            return None
    return figma_service
