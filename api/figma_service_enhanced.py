import os
import requests
import base64
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class FigmaComponent:
    id: str
    name: str
    type: str
    styles: Dict[str, Any]
    bounds: Dict[str, Any]
    svg_data: Optional[str] = None

class FigmaService:
    def __init__(self, api_token: str, file_id: str):
        self.api_token = api_token
        self.file_id = file_id
        self.api_base = "https://api.figma.com/v1"
    
    def fetch_components(self) -> List[FigmaComponent]:
        """Fetch all components from the Figma file."""
        try:
            response = requests.get(
                f"{self.api_base}/files/{self.file_id}",
                headers={"X-Figma-Token": self.api_token}
            )
            response.raise_for_status()
            data = response.json()
            
            components = []
            
            # Find all components and frames in the file
            def traverse_node(node, parent_path=""):
                current_path = f"{parent_path}/{node['name']}" if parent_path else node['name']
                
                # Handle both COMPONENT and FRAME types
                if node.get('type') in ['COMPONENT', 'FRAME']:
                    component = self._parse_component(node, current_path)
                    if component:
                        components.append(component)
                
                if 'children' in node:
                    for child in node['children']:
                        traverse_node(child, current_path)
            
            # Start traversal from document root
            if 'document' in data and 'children' in data['document']:
                for page in data['document']['children']:
                    if 'children' in page:
                        for child in page['children']:
                            traverse_node(child)
            
            print(f"Found {len(components)} components")
            return components
            
        except Exception as e:
            print(f"Error fetching components: {str(e)}")
            return []
    
    def _parse_component(self, node: Dict, full_name: str) -> Optional[FigmaComponent]:
        """Parse a single component and extract its styling."""
        try:
            styles = self._extract_styles(node)
            
            # For text components, also extract text-specific styles
            if node.get('type') == 'TEXT':
                text_styles = self._extract_text_styles(node)
                styles.update(text_styles)
            
            # Extract child elements if they exist (for component sets)
            child_elements = {}
            if 'children' in node:
                self._extract_child_elements(node['children'], child_elements)
                styles.update(child_elements)
            
            # Determine component type based on name and node type
            name_lower = node['name'].lower()
            if node.get('type') == 'TEXT':
                component_type = 'text'
            else:
                component_type = self._determine_component_type(name_lower)
            
            return FigmaComponent(
                id=node['id'],
                name=full_name,
                type=component_type,
                styles=styles,
                bounds=node.get('absoluteBoundingBox', {})
            )
        except Exception as e:
            print(f"Failed to parse component {full_name}: {str(e)}")
            return None
    
    def _extract_child_elements(self, children: List[Dict], child_elements: Dict, prefix: str = ""):
        """Recursively extract styling from child elements (text, nested groups, etc.)."""
        for child in children:
            child_name = child.get('name', '').lower()
            child_type = child.get('type', '')
            
            # Handle text elements
            if child_type == 'TEXT':
                text_styles = self._extract_text_styles(child)
                
                # Map text elements to our visual settings
                if 'distance' in child_name:
                    child_elements['distanceTextColor'] = text_styles.get('color')
                    child_elements['distanceTextSize'] = text_styles.get('fontSize')
                    child_elements['distanceTextFamily'] = text_styles.get('fontFamily')
                    child_elements['distanceTextWeight'] = text_styles.get('fontWeight')
                elif 'object' in child_name:
                    child_elements['objectTypeTextColor'] = text_styles.get('color')
                    child_elements['objectTypeTextSize'] = text_styles.get('fontSize')
                    child_elements['objectTypeTextFamily'] = text_styles.get('fontFamily')
                    child_elements['objectTypeTextWeight'] = text_styles.get('fontWeight')
                elif 'id' in child_name:
                    child_elements['personIdTextColor'] = text_styles.get('color')
                    child_elements['personIdTextSize'] = text_styles.get('fontSize')
                    child_elements['personIdTextFamily'] = text_styles.get('fontFamily')
                    child_elements['personIdTextWeight'] = text_styles.get('fontWeight')
            
            # Recursively process nested groups/frames
            elif 'children' in child:
                self._extract_child_elements(child['children'], child_elements, f"{prefix}{child_name}_")
    
    def _extract_text_styles(self, text_node: Dict) -> Dict[str, Any]:
        """Extract comprehensive text styling from a text node."""
        styles = {}
        
        # Extract fill color
        if 'fills' in text_node and text_node['fills']:
            fill = text_node['fills'][0]
            if fill.get('type') == 'SOLID' and 'color' in fill:
                color = fill['color']
                styles['color'] = self._rgba_to_hex(color)
        
        # Extract text style properties
        if 'style' in text_node:
            text_style = text_node['style']
            styles['fontSize'] = text_style.get('fontSize', 12)
            styles['fontFamily'] = text_style.get('fontFamily', 'Arial')
            styles['fontWeight'] = text_style.get('fontWeight', 400)
            styles['lineHeight'] = text_style.get('lineHeightPx', 'normal')
            styles['letterSpacing'] = text_style.get('letterSpacing', 0)
            styles['textAlign'] = text_style.get('textAlignHorizontal', 'left').lower()
        
        return styles
    
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
    
    def _rgba_to_hex(self, color: Dict[str, float]) -> str:
        """Convert RGBA color to hex format."""
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
        settings = {'boxStyle': 'solid'}  # Default value
        
        # Group related components by their base name (e.g., person-box-locked)
        component_groups = {}
        for component in components:
            name = component.name.lower()
            
            # Find the base component name
            base_name = None
            for base in ['person-box-locked', 'person-box-unlocked', 'person-box-far', 'person-box-grey']:
                if base in name:
                    base_name = base
                    break
            
            if base_name:
                if base_name not in component_groups:
                    component_groups[base_name] = []
                component_groups[base_name].append(component)
        
        # Process each component group
        for base_name, group_components in component_groups.items():
            # Find the main component (exact match to base name)
            main_component = None
            child_components = []
            
            for comp in group_components:
                if comp.name.lower().endswith(base_name):
                    main_component = comp
                else:
                    child_components.append(comp)
            
            if main_component:
                self._map_component_group_to_settings(main_component, child_components, settings)
        
        return settings
    
    def _map_component_group_to_settings(self, main_component: FigmaComponent, child_components: List[FigmaComponent], settings: Dict[str, Any]):
        """Map a component group (main + children) to visual settings."""
        name_lower = main_component.name.lower()
        main_styles = main_component.styles
        
        # Determine the component state
        state_mapping = {
            'locked': {
                'color': 'personLockedBoxColor',
                'bg_color': 'personLockedBoxBackgroundColor',
                'bg_opacity': 'personLockedBoxBackgroundOpacity',
                'border_radius': 'personLockedBoxBorderRadius',
                'stroke_width': 'personLockedBoxStrokeWidth',
                'text_color': 'personIdLockedTextColor'
            },
            'unlocked': {
                'color': 'personUnlockedBoxColor',
                'bg_color': 'personUnlockedBoxBackgroundColor',
                'bg_opacity': 'personUnlockedBoxBackgroundOpacity',
                'border_radius': 'personUnlockedBoxBorderRadius',
                'stroke_width': 'personUnlockedBoxStrokeWidth',
                'text_color': 'personIdTextColor'
            },
            'far': {
                'color': 'personFarBoxColor',
                'bg_color': 'personFarBoxBackgroundColor',
                'bg_opacity': 'personFarBoxBackgroundOpacity',
                'border_radius': 'personFarBoxBorderRadius',
                'stroke_width': 'personFarBoxStrokeWidth',
                'text_color': 'personIdTextColor'
            },
            'grey': {
                'color': 'personGreyColor',
                'bg_color': 'personGreyBackgroundColor',
                'bg_opacity': 'personGreyBackgroundOpacity',
                'border_radius': 'personGreyBorderRadius',
                'stroke_width': 'personGreyStrokeWidth',
                'text_color': 'personIdTextColor'
            }
        }
        
        # Determine which state this is
        current_state = None
        for state in ['unlocked', 'locked', 'far', 'grey']:
            if state in name_lower:
                current_state = state
                break
        
        if not current_state:
            return
        
        mapping = state_mapping[current_state]
        
        # Map main component properties
        if main_styles.get('borderColor'):
            settings[mapping['color']] = main_styles['borderColor']
        elif main_styles.get('color'):
            settings[mapping['color']] = main_styles['color']
        
        if main_styles.get('backgroundColor'):
            settings[mapping['bg_color']] = main_styles['backgroundColor']
            settings[mapping['bg_opacity']] = main_styles.get('backgroundOpacity', 0.2)
        
        if 'borderRadius' in main_styles:
            settings[mapping['border_radius']] = main_styles['borderRadius']
        
        if 'borderWidth' in main_styles:
            settings[mapping['stroke_width']] = int(main_styles['borderWidth'])
        
        # Process child components for text styling
        for child in child_components:
            child_name = child.name.lower()
            child_styles = child.styles
            
            if 'id' in child_name:
                # Extract text styles from ID components
                self._extract_text_properties_from_component(child, settings, mapping['text_color'], 'personId')
            elif 'object' in child_name:
                # Extract text styles from object label components
                self._extract_text_properties_from_component(child, settings, 'objectTypeTextColor', 'objectType')
            elif 'distance' in child_name:
                # Extract text styles from distance components
                self._extract_text_properties_from_component(child, settings, 'distanceTextColor', 'distance')
    
    def _extract_text_properties_from_component(self, component: FigmaComponent, settings: Dict[str, Any], color_key: str, prefix: str):
        """Extract text properties from a component and its children, looking for TEXT nodes."""
        # This component might contain TEXT children, we need to fetch its details
        try:
            response = requests.get(
                f"{self.api_base}/files/{self.file_id}/nodes?ids={component.id}",
                headers={"X-Figma-Token": self.api_token}
            )
            response.raise_for_status()
            data = response.json()
            
            if 'nodes' in data and component.id in data['nodes']:
                node = data['nodes'][component.id]['document']
                self._extract_text_from_node(node, settings, color_key, prefix)
                
        except Exception as e:
            print(f"Failed to fetch details for component {component.name}: {str(e)}")
    
    def _extract_text_from_node(self, node: Dict, settings: Dict[str, Any], color_key: str, prefix: str):
        """Recursively extract text properties from a node and its children."""
        if node.get('type') == 'TEXT':
            # Extract text styles
            text_styles = self._extract_text_styles(node)
            if text_styles.get('color'):
                settings[color_key] = text_styles['color']
            if text_styles.get('fontSize'):
                settings[f'{prefix}TextSize'] = text_styles['fontSize']
            if text_styles.get('fontFamily'):
                settings[f'{prefix}TextFamily'] = text_styles['fontFamily']
            if text_styles.get('fontWeight'):
                settings[f'{prefix}TextWeight'] = text_styles['fontWeight']
        
        # Recursively check children
        if 'children' in node:
            for child in node['children']:
                self._extract_text_from_node(child, settings, color_key, prefix)

def get_figma_service() -> Optional[FigmaService]:
    """Get configured Figma service instance."""
    api_token = os.getenv('FIGMA_API_TOKEN')
    file_id = os.getenv('FIGMA_FILE_ID')
    
    if not api_token or not file_id:
        raise ValueError("Figma service not configured. Please set FIGMA_API_TOKEN and FIGMA_FILE_ID environment variables.")
    
    return FigmaService(api_token, file_id)
