import os
import requests
import base64
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class FigmaDiagnostic:
    level: str  # 'error', 'warning', 'info'
    category: str  # 'missing_component', 'missing_text', 'missing_property', 'api_error'
    component_name: str
    message: str
    suggestion: str

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
        self.diagnostics: List[FigmaDiagnostic] = []
    
    def add_diagnostic(self, level: str, category: str, component_name: str, message: str, suggestion: str):
        """Add a diagnostic message to track issues during sync."""
        diagnostic = FigmaDiagnostic(
            level=level,
            category=category,
            component_name=component_name,
            message=message,
            suggestion=suggestion
        )
        self.diagnostics.append(diagnostic)
        
        # Also log to console
        icon = "❌" if level == "error" else "⚠️" if level == "warning" else "ℹ️"
        print(f"{icon} [{category}] {component_name}: {message}")
        print(f"   💡 {suggestion}")
    
    def get_diagnostics_summary(self) -> List[Dict[str, str]]:
        """Get formatted diagnostics for API response."""
        return [
            {
                'level': d.level,
                'category': d.category,
                'component_name': d.component_name,
                'message': d.message,
                'suggestion': d.suggestion
            }
            for d in self.diagnostics
        ]
    
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
            self.add_diagnostic(
                'error',
                'api_error',
                'Figma API',
                f'Failed to fetch components: {str(e)}',
                'Check your FIGMA_API_TOKEN and FIGMA_FILE_ID environment variables, and verify your network connection.'
            )
            return []
    
    def fetch_component_svg(self, component_id: str) -> Optional[str]:
        """Fetch SVG representation of a component."""
        try:
            response = requests.get(
                f"{self.api_base}/images/{self.file_id}?ids={component_id}&format=svg",
                headers={"X-Figma-Token": self.api_token}
            )
            response.raise_for_status()
            data = response.json()
            
            if 'images' in data and component_id in data['images']:
                svg_url = data['images'][component_id]
                if svg_url:
                    svg_response = requests.get(svg_url)
                    svg_response.raise_for_status()
                    return svg_response.text
            
            return None
            
        except Exception as e:
            self.add_diagnostic(
                'warning',
                'api_error',
                component_id,
                f'Failed to fetch SVG data: {str(e)}',
                'SVG components (crosshair, tracking-dot) will use default rendering. Check your Figma API access.'
            )
            return None
    
    def fetch_component_png(self, component_id: str) -> Optional[str]:
        """Fetch PNG representation of a component with transparent background."""
        try:
            # Request PNG format with 2x scale for better quality
            response = requests.get(
                f"{self.api_base}/images/{self.file_id}?ids={component_id}&format=png&scale=2",
                headers={"X-Figma-Token": self.api_token}
            )
            response.raise_for_status()
            data = response.json()
            
            if 'images' in data and component_id in data['images']:
                png_url = data['images'][component_id]
                if png_url:
                    png_response = requests.get(png_url)
                    png_response.raise_for_status()
                    # Convert to base64 data URL
                    png_base64 = base64.b64encode(png_response.content).decode()
                    return f"data:image/png;base64,{png_base64}"
            
            return None
            
        except Exception as e:
            self.add_diagnostic(
                'warning',
                'api_error',
                component_id,
                f'Failed to fetch PNG data: {str(e)}',
                'Crosshair will use default canvas rendering. Check your Figma API access.'
            )
            return None
    
    def fetch_component_variants(self, component_name: str) -> Optional[Dict[str, Any]]:
        """Fetch component with variants (e.g., Body-Tracker with Charging/Ready states)."""
        try:
            # First, fetch the file to find the component with variants
            response = requests.get(
                f"{self.api_base}/files/{self.file_id}",
                headers={"X-Figma-Token": self.api_token}
            )
            response.raise_for_status()
            data = response.json()
            
            # Find the component with the specified name
            component_node = None
            component_set_id = None
            all_matching_components = []  # Track all components that match the name
            
            def find_component(node, target_name):
                nonlocal component_node, component_set_id
                node_name = node.get('name', '')
                node_type = node.get('type', '')
                
                # Check if this matches our target name (exact or base name)
                base_name = node_name.split('/')[0] if '/' in node_name else node_name
                if base_name.lower() == target_name.lower():
                    all_matching_components.append({
                        'name': node_name,
                        'type': node_type,
                        'id': node.get('id'),
                        'has_children': 'children' in node,
                        'has_component_properties': 'componentProperties' in node
                    })
                    
                    # Check if this is a component set (has variants)
                    if node_type == 'COMPONENT_SET':
                        component_set_id = node.get('id')
                        component_node = node
                        return True
                
                if 'children' in node:
                    for child in node['children']:
                        if find_component(child, target_name):
                            return True
                return False
            
            # Search through document
            if 'document' in data:
                find_component(data['document'], component_name)
            
            # Debug: Print all matching components
            print(f"\n🔍 DEBUG: Found {len(all_matching_components)} components matching '{component_name}':")
            for comp in all_matching_components:
                print(f"  - {comp['name']} (type: {comp['type']}, has_children: {comp['has_children']}, has_props: {comp['has_component_properties']})")
            
            if not component_node:
                # Try to find individual variant components instead
                print(f"⚠️ No COMPONENT_SET found, looking for individual COMPONENT nodes...")
                variants = {}
                
                for comp_info in all_matching_components:
                    if comp_info['type'] == 'COMPONENT':
                        # This is an individual variant component
                        # Extract the variant name from the full name (e.g., "body-tracker/State=charging" -> "charging")
                        full_name = comp_info['name']
                        if '=' in full_name:
                            variant_name = full_name.split('=')[-1].lower()
                            print(f"  Found variant: {variant_name} from {full_name}")
                            
                            # Fetch the full node data for this component
                            node_response = requests.get(
                                f"{self.api_base}/files/{self.file_id}/nodes?ids={comp_info['id']}",
                                headers={"X-Figma-Token": self.api_token}
                            )
                            node_response.raise_for_status()
                            node_data = node_response.json()
                            
                            if 'nodes' in node_data and comp_info['id'] in node_data['nodes']:
                                variant_node = node_data['nodes'][comp_info['id']]['document']
                                variant_data = self._parse_variant_component(variant_node, variant_name=variant_name)
                                if variant_data:
                                    variants[variant_name] = variant_data
                                    print(f"  ✅ Extracted properties for {variant_name}: {list(variant_data.get('properties', {}).keys())}")
                
                if variants:
                    print(f"✅ Successfully extracted {len(variants)} variants from individual components")
                    return {
                        'component_id': all_matching_components[0]['id'] if all_matching_components else None,
                        'component_name': component_name,
                        'variants': variants
                    }
                
                self.add_diagnostic(
                    'warning',
                    'missing_component',
                    component_name,
                    f'Component "{component_name}" not found as COMPONENT_SET in Figma file',
                    f'Found {len(all_matching_components)} matching components but none were COMPONENT_SET type.'
                )
                return None
            
            # Extract variants from the component set
            variants = {}
            if 'children' in component_node:
                print(f"🔍 DEBUG: COMPONENT_SET has {len(component_node['children'])} children")
                for idx, variant_node in enumerate(component_node['children']):
                    # Each child is a variant
                    print(f"  Child {idx}: name={variant_node.get('name')}, type={variant_node.get('type')}")
                    variant_props = variant_node.get('componentProperties', {})
                    print(f"    componentProperties: {list(variant_props.keys())}")
                    
                    # Try multiple strategies to get the variant name
                    state_value = None
                    
                    # Strategy 1: Look for "State" property in componentProperties
                    for prop_name, prop_data in variant_props.items():
                        print(f"      Found property: {prop_name} = {prop_data}")
                        if prop_name.lower() == 'state':
                            state_value = prop_data.get('value', '').lower()
                            print(f"    ✅ Found State property: {state_value}")
                            break
                    
                    # Strategy 2: Extract from the node name (e.g., "State=charging")
                    if not state_value:
                        node_name = variant_node.get('name', '')
                        if '=' in node_name:
                            state_value = node_name.split('=')[-1].lower()
                            print(f"    ✅ Extracted from name: {state_value}")
                    
                    if state_value:
                        # Parse this variant's properties
                        variant_data = self._parse_variant_component(variant_node, variant_name=state_value)
                        if variant_data:
                            variants[state_value] = variant_data
                            print(f"    ✅ Successfully parsed variant: {state_value}")
                    else:
                        print(f"    ❌ Could not determine variant name for child {idx}")
            
            if not variants:
                self.add_diagnostic(
                    'warning',
                    'missing_property',
                    component_name,
                    'No variants found with "State" property',
                    'In Figma, add a "State" variant property to your component set.'
                )
                return None
            
            return {
                'component_id': component_set_id,
                'component_name': component_name,
                'variants': variants
            }
            
        except Exception as e:
            self.add_diagnostic(
                'error',
                'api_error',
                component_name,
                f'Failed to fetch component variants: {str(e)}',
                'Check your Figma API access and component structure.'
            )
            print(f"❌ Exception in fetch_component_variants: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_variant_component(self, node: Dict, variant_name: str) -> Optional[Dict[str, Any]]:
        """Parse a variant component and extract properties from child nodes recursively."""
        try:
            variant_data = {
                'id': node.get('id'),
                'name': variant_name,
                'bounds': node.get('absoluteBoundingBox', {}),
                'properties': {}
            }
            
            # Extract properties from the variant node itself FIRST
            self._extract_all_visual_properties(node, variant_data['properties'])
            print(f"  📋 Extracted from parent node: {list(variant_data['properties'].keys())}")
            
            # Recursively extract properties from ALL descendants
            self._extract_from_descendants(node, variant_data['properties'], level=1)
            
            print(f"  ✅ Final properties for {variant_name}: {list(variant_data['properties'].keys())}")
            
            # Even if no specific properties were extracted, return the variant data
            # The frontend will handle missing properties gracefully
            return variant_data
            
        except Exception as e:
            print(f"Failed to parse variant component {variant_name}: {str(e)}")
            return None
    
    def _extract_from_descendants(self, node: Dict, properties: Dict[str, Any], level: int = 0):
        """Recursively extract visual properties from all descendant nodes."""
        if 'children' not in node:
            return
        
        indent = "  " * level
        for child in node['children']:
            child_name = child.get('name', 'unnamed')
            child_type = child.get('type', 'unknown')
            
            # Extract properties from this child
            child_props = {}
            self._extract_all_visual_properties(child, child_props)
            
            if child_props:
                print(f"{indent}📋 Extracted from {child_type} '{child_name}': {list(child_props.keys())}")
                
                # Only add child properties that aren't already set by parent
                for key, value in child_props.items():
                    if key not in properties or properties[key] == 0:
                        properties[key] = value
            
            # Recursively process grandchildren
            if 'children' in child:
                self._extract_from_descendants(child, properties, level + 1)
    
    def _extract_all_visual_properties(self, node: Dict, properties: Dict[str, Any]):
        """Extract all visual properties from a Figma node."""
        try:
            # Extract fills (background/fill color)
            fills = node.get('fills', [])
            if fills and len(fills) > 0:
                fill = fills[0]
                if fill.get('type') == 'SOLID':
                    color = fill.get('color', {})
                    opacity = fill.get('opacity', 1.0)
                    r = int(color.get('r', 0) * 255)
                    g = int(color.get('g', 0) * 255)
                    b = int(color.get('b', 0) * 255)
                    a = opacity
                    properties['fillColor'] = f'rgba({r}, {g}, {b}, {a})'
                    properties['backgroundColor'] = f'rgba({r}, {g}, {b}, {a})'
            
            # Extract strokes (border color)
            strokes = node.get('strokes', [])
            if strokes and len(strokes) > 0:
                stroke = strokes[0]
                if stroke.get('type') == 'SOLID':
                    color = stroke.get('color', {})
                    opacity = stroke.get('opacity', 1.0)
                    r = int(color.get('r', 0) * 255)
                    g = int(color.get('g', 0) * 255)
                    b = int(color.get('b', 0) * 255)
                    a = opacity
                    properties['strokeColor'] = f'rgba({r}, {g}, {b}, {a})'
                    properties['borderColor'] = f'rgba({r}, {g}, {b}, {a})'
            
            # Extract stroke/border width
            stroke_weight = node.get('strokeWeight', 0)
            if stroke_weight > 0:
                properties['strokeWidth'] = stroke_weight
                properties['borderWidth'] = stroke_weight
            
            # Extract dimensions from bounds
            bounds = node.get('absoluteBoundingBox', {})
            if bounds:
                properties['width'] = bounds.get('width', 0)
                properties['height'] = bounds.get('height', 0)
            
            # Extract corner radius
            corner_radius = node.get('cornerRadius', 0)
            if corner_radius > 0:
                properties['borderRadius'] = corner_radius
                properties['cornerRadius'] = corner_radius
            
            # Extract individual corner radii (for advanced border radius)
            rect_corner_radii = node.get('rectangleCornerRadii')
            if rect_corner_radii:
                properties['rectangleCornerRadii'] = rect_corner_radii
            
            # Extract opacity
            opacity = node.get('opacity', 1.0)
            if opacity != 1.0:
                properties['opacity'] = opacity
            
            # Extract blend mode
            blend_mode = node.get('blendMode')
            if blend_mode and blend_mode != 'NORMAL':
                properties['blendMode'] = blend_mode
            
            # Extract effects (shadows, blurs, etc.)
            effects = node.get('effects', [])
            if effects:
                properties['effects'] = effects
                # Parse common effects
                for effect in effects:
                    effect_type = effect.get('type')
                    if effect_type == 'DROP_SHADOW':
                        properties['dropShadow'] = effect
                    elif effect_type == 'INNER_SHADOW':
                        properties['innerShadow'] = effect
                    elif effect_type == 'LAYER_BLUR':
                        properties['blur'] = effect
            
            # Extract layout properties (auto-layout)
            layout_mode = node.get('layoutMode')
            if layout_mode:
                properties['layoutMode'] = layout_mode  # HORIZONTAL, VERTICAL, NONE
                properties['primaryAxisSizingMode'] = node.get('primaryAxisSizingMode')
                properties['counterAxisSizingMode'] = node.get('counterAxisSizingMode')
                properties['primaryAxisAlignItems'] = node.get('primaryAxisAlignItems')
                properties['counterAxisAlignItems'] = node.get('counterAxisAlignItems')
                properties['paddingLeft'] = node.get('paddingLeft', 0)
                properties['paddingRight'] = node.get('paddingRight', 0)
                properties['paddingTop'] = node.get('paddingTop', 0)
                properties['paddingBottom'] = node.get('paddingBottom', 0)
                properties['itemSpacing'] = node.get('itemSpacing', 0)
                properties['counterAxisSpacing'] = node.get('counterAxisSpacing', 0)
            
            # Extract constraints
            constraints = node.get('constraints')
            if constraints:
                properties['constraints'] = constraints
            
            # Extract layout positioning
            layout_align = node.get('layoutAlign')
            if layout_align:
                properties['layoutAlign'] = layout_align
            
            layout_grow = node.get('layoutGrow')
            if layout_grow:
                properties['layoutGrow'] = layout_grow
            
            # Extract absolute positioning
            properties['absoluteX'] = node.get('x', 0)
            properties['absoluteY'] = node.get('y', 0)
            
            # Extract text properties if it's a text node
            if node.get('type') == 'TEXT':
                style = node.get('style', {})
                if 'fontSize' in style:
                    properties['fontSize'] = style['fontSize']
                if 'fontFamily' in style:
                    properties['fontFamily'] = style['fontFamily']
                if 'fontWeight' in style:
                    properties['fontWeight'] = style['fontWeight']
                if 'letterSpacing' in style:
                    properties['letterSpacing'] = style['letterSpacing']
                if 'lineHeight' in style:
                    line_height = style['lineHeight']
                    if isinstance(line_height, dict):
                        properties['lineHeight'] = line_height.get('value', 'auto')
                    else:
                        properties['lineHeight'] = line_height
                if 'textAlignHorizontal' in style:
                    properties['textAlign'] = style['textAlignHorizontal']
                if 'textAlignVertical' in style:
                    properties['textAlignVertical'] = style['textAlignVertical']
                if 'textDecoration' in style:
                    properties['textDecoration'] = style['textDecoration']
                if 'textCase' in style:
                    properties['textCase'] = style['textCase']
                
                # Extract text content
                characters = node.get('characters')
                if characters:
                    properties['text'] = characters
            
            # Extract clipping and masking
            if node.get('clipsContent'):
                properties['clipsContent'] = True
            if node.get('isMask'):
                properties['isMask'] = True
            
            # Extract visibility
            if not node.get('visible', True):
                properties['visible'] = False
            
            # Extract rotation
            rotation = node.get('rotation', 0)
            if rotation != 0:
                properties['rotation'] = rotation
            
            # Determine and store shape type
            node_type = node.get('type', '')
            if node_type == 'ELLIPSE':
                properties['shape'] = 'circle'
            elif node_type == 'RECTANGLE':
                if corner_radius > 0:
                    properties['shape'] = 'rounded-rectangle'
                else:
                    properties['shape'] = 'rectangle'
            elif node_type == 'TEXT':
                properties['shape'] = 'text'
            elif node_type == 'FRAME':
                properties['shape'] = 'frame'
            elif node_type == 'GROUP':
                properties['shape'] = 'group'
            elif node_type:
                properties['shape'] = node_type.lower()
            
            # Store component type
            properties['componentType'] = node_type
            
            # Store component name
            properties['componentName'] = node.get('name', '')
            
            # Extract any additional properties that might be useful
            # Store raw transform matrix if available
            if 'relativeTransform' in node:
                properties['transform'] = node['relativeTransform']
            
            # Extract stroke align (CENTER, INSIDE, OUTSIDE)
            stroke_align = node.get('strokeAlign')
            if stroke_align:
                properties['strokeAlign'] = stroke_align
            
            # Extract stroke cap and join
            if node.get('strokeCap'):
                properties['strokeCap'] = node['strokeCap']
            if node.get('strokeJoin'):
                properties['strokeJoin'] = node['strokeJoin']
            
        except Exception as e:
            print(f"Failed to extract properties from node: {str(e)}")
    
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
                # Use fill-level opacity (the one set in Figma UI) instead of color-level alpha
                fill_opacity = fill.get('opacity', color.get('a', 1.0))
                
                styles['color'] = self._rgba_to_hex(color)
                styles['opacity'] = fill_opacity
                # Store backgroundColor as RGBA string using the fill opacity
                styles['backgroundColor'] = self._rgba_to_rgba_string_with_opacity(color, fill_opacity)
                styles['backgroundOpacity'] = fill_opacity
        
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
    
    def _rgba_to_rgba_string_with_opacity(self, color: Dict[str, float], opacity: float) -> str:
        """Convert RGBA color to rgba() string format with custom opacity."""
        r = int(color.get('r', 0) * 255)
        g = int(color.get('g', 0) * 255)
        b = int(color.get('b', 0) * 255)
        return f"rgba({r}, {g}, {b}, {opacity})"
    
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
        
        # Check for crosshair first (before bounding-box check)
        if 'crosshair' in name_lower:
            return 'crosshair'
        elif any(keyword in name_lower for keyword in ['bounding-box', 'bbox', 'box']):
            if 'person' in name_lower:
                return 'person-box'
            elif 'vehicle' in name_lower:
                return 'vehicle-box'
            else:
                return 'bounding-box'
        elif any(keyword in name_lower for keyword in ['reticle', 'target']):
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
        expected_bases = ['person-box-locked', 'person-box-unlocked', 'person-box-far', 'person-box-grey']
        
        for component in components:
            name = component.name.lower()
            
            # Find the base component name
            base_name = None
            for base in expected_bases:
                if base in name:
                    base_name = base
                    break
            
            if base_name:
                if base_name not in component_groups:
                    component_groups[base_name] = []
                component_groups[base_name].append(component)
        
        # Check for missing expected components
        for expected_base in expected_bases:
            if expected_base not in component_groups:
                state_name = expected_base.replace('person-box-', '').title()
                self.add_diagnostic(
                    'warning',
                    'missing_component',
                    expected_base,
                    f'Missing expected component for {state_name} state',
                    f'In Figma, create a component named "{expected_base}" with child frames for -id, -object, and -distance text.'
                )
        
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
            else:
                self.add_diagnostic(
                    'warning',
                    'missing_component',
                    base_name,
                    f'Found child components but missing main component',
                    f'In Figma, ensure you have a component named exactly "{base_name}" (not just child components).'
                )
        
        # Process crosshair components
        crosshair_components = {}
        for component in components:
            name_lower = component.name.lower()
            if 'crosshair-default' in name_lower:
                crosshair_components['default'] = component
            elif 'crosshair-active' in name_lower:
                crosshair_components['active'] = component
        
        # Check for missing crosshair components
        if 'default' not in crosshair_components:
            self.add_diagnostic(
                'warning',
                'missing_component',
                'Crosshair-Default',
                'Missing default crosshair component',
                'In Figma, create a frame named "Crosshair-Default" with a shape named "cursorShape".'
            )
        if 'active' not in crosshair_components:
            self.add_diagnostic(
                'warning',
                'missing_component',
                'Crosshair-Active',
                'Missing active crosshair component',
                'In Figma, create a frame named "Crosshair-Active" with a shape named "cursorShape".'
            )
        
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
                'text_color': 'personIdLockedTextColor',
                'object_text_color': 'objectTypeLockedTextColor',
                'object_text_size': 'objectTypeLockedTextSize',
                'object_text_family': 'objectTypeLockedTextFamily',
                'object_text_weight': 'objectTypeLockedTextWeight',
                'distance_text_color': 'distanceLockedTextColor',
                'distance_text_size': 'distanceLockedTextSize',
                'distance_text_family': 'distanceLockedTextFamily',
                'distance_text_weight': 'distanceLockedTextWeight'
            },
            'unlocked': {
                'color': 'personUnlockedBoxColor',
                'bg_color': 'personUnlockedBoxBackgroundColor',
                'bg_opacity': 'personUnlockedBoxBackgroundOpacity',
                'border_radius': 'personUnlockedBoxBorderRadius',
                'stroke_width': 'personUnlockedBoxStrokeWidth',
                'text_color': 'personIdTextColor',
                'object_text_color': 'objectTypeTextColor',
                'object_text_size': 'objectTypeTextSize',
                'object_text_family': 'objectTypeTextFamily',
                'object_text_weight': 'objectTypeTextWeight',
                'distance_text_color': 'distanceTextColor',
                'distance_text_size': 'distanceTextSize',
                'distance_text_family': 'distanceTextFamily',
                'distance_text_weight': 'distanceTextWeight'
            },
            'far': {
                'color': 'personFarBoxColor',
                'bg_color': 'personFarBoxBackgroundColor',
                'bg_opacity': 'personFarBoxBackgroundOpacity',
                'border_radius': 'personFarBoxBorderRadius',
                'stroke_width': 'personFarBoxStrokeWidth',
                'text_color': 'personIdFarTextColor',
                'object_text_color': 'objectTypeFarTextColor',
                'object_text_size': 'objectTypeFarTextSize',
                'object_text_family': 'objectTypeFarTextFamily',
                'object_text_weight': 'objectTypeFarTextWeight',
                'distance_text_color': 'distanceFarTextColor',
                'distance_text_size': 'distanceFarTextSize',
                'distance_text_family': 'distanceFarTextFamily',
                'distance_text_weight': 'distanceFarTextWeight'
            },
            'grey': {
                'color': 'personGreyColor',
                'bg_color': 'personGreyBackgroundColor',
                'bg_opacity': 'personGreyBackgroundOpacity',
                'border_radius': 'personGreyBorderRadius',
                'stroke_width': 'personGreyStrokeWidth',
                'text_color': 'personIdGreyTextColor',
                'object_text_color': 'objectTypeGreyTextColor',
                'object_text_size': 'objectTypeGreyTextSize',
                'object_text_family': 'objectTypeGreyTextFamily',
                'object_text_weight': 'objectTypeGreyTextWeight',
                'distance_text_color': 'distanceGreyTextColor',
                'distance_text_size': 'distanceGreyTextSize',
                'distance_text_family': 'distanceGreyTextFamily',
                'distance_text_weight': 'distanceGreyTextWeight'
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
        
        # Track which child components we found
        found_children = {'id': False, 'object': False, 'distance': False}
        
        # Process child components for text styling and frame background colors
        for child in child_components:
            child_name = child.name.lower()
            child_styles = child.styles
            
            if 'id' in child_name:
                found_children['id'] = True
                # Extract text styles from ID components and frame background color
                self._extract_text_properties_from_component(child, settings, mapping['text_color'], 'personId')
                # Extract frame fill color for ID text background
                self._extract_frame_background_color(child, settings, current_state, 'id')
            elif 'object' in child_name:
                found_children['object'] = True
                # Extract state-specific object text styles and frame background color
                self._extract_text_properties_from_component(child, settings, mapping['object_text_color'], 'objectType', mapping)
                # Extract frame fill color for object text background
                self._extract_frame_background_color(child, settings, current_state, 'object')
            elif 'distance' in child_name:
                found_children['distance'] = True
                # Extract state-specific distance text styles and frame background color
                self._extract_text_properties_from_component(child, settings, mapping['distance_text_color'], 'distance', mapping)
                # Extract frame fill color for distance text background
                self._extract_frame_background_color(child, settings, current_state, 'distance')
        
        # Report missing child components
        if not found_children['id']:
            self.add_diagnostic(
                'warning',
                'missing_component',
                main_component.name,
                'Missing ID text child component',
                f'In Figma, add a child frame named "{main_component.name}-id" with a TEXT layer for ID styling.'
            )
        if not found_children['object']:
            self.add_diagnostic(
                'warning',
                'missing_component',
                main_component.name,
                'Missing Object Type text child component',
                f'In Figma, add a child frame named "{main_component.name}-object" with a TEXT layer for object type styling.'
            )
        if not found_children['distance']:
            self.add_diagnostic(
                'warning',
                'missing_component',
                main_component.name,
                'Missing Distance text child component',
                f'In Figma, add a child frame named "{main_component.name}-distance" with a TEXT layer for distance styling.'
            )
    
    def _extract_frame_background_color(self, component: FigmaComponent, settings: Dict[str, Any], state: str, frame_type: str):
        """Extract frame fill color for text background boxes."""
        try:
            response = requests.get(
                f"{self.api_base}/files/{self.file_id}/nodes?ids={component.id}",
                headers={"X-Figma-Token": self.api_token}
            )
            response.raise_for_status()
            data = response.json()
            
            if 'nodes' in data and component.id in data['nodes']:
                node = data['nodes'][component.id]['document']
                
                # Extract frame fill color
                if node.get('fills') and len(node['fills']) > 0:
                    fill = node['fills'][0]  # Take the first fill
                    if fill.get('type') == 'SOLID' and fill.get('color'):
                        fill_color = fill['color']
                        opacity = fill.get('opacity', 1.0)
                        
                        # Create property name based on state and frame type
                        if frame_type == 'object':
                            if state == 'locked':
                                property_name = 'objectTypeLockedBackgroundColor'
                            elif state == 'far':
                                property_name = 'objectTypeFarBackgroundColor'
                            elif state == 'grey':
                                property_name = 'objectTypeGreyBackgroundColor'
                            else:  # unlocked
                                property_name = 'objectTypeBackgroundColor'
                        elif frame_type == 'distance':
                            if state == 'locked':
                                property_name = 'distanceLockedBackgroundColor'
                            elif state == 'far':
                                property_name = 'distanceFarBackgroundColor'
                            elif state == 'grey':
                                property_name = 'distanceGreyBackgroundColor'
                            else:  # unlocked
                                property_name = 'distanceBackgroundColor'
                        elif frame_type == 'id':
                            if state == 'locked':
                                property_name = 'personIdLockedBackgroundColor'
                            elif state == 'far':
                                property_name = 'personIdFarBackgroundColor'
                            elif state == 'grey':
                                property_name = 'personIdGreyBackgroundColor'
                            else:  # unlocked
                                property_name = 'personIdBackgroundColor'
                        
                        # Store as RGBA string with opacity
                        rgba_color = self._rgba_to_rgba_string_with_opacity(fill_color, opacity)
                        settings[property_name] = rgba_color
                        
                        # Also store opacity separately if needed
                        opacity_property = property_name.replace('BackgroundColor', 'BackgroundOpacity')
                        settings[opacity_property] = opacity
                        
                        # Extract auto layout padding if available
                        if node.get('layoutMode') and node.get('paddingLeft') is not None:
                            padding_property = property_name.replace('BackgroundColor', 'Padding')
                            # Use horizontal padding (assuming symmetric)
                            padding = node.get('paddingLeft', 0)
                            settings[padding_property] = padding
                
        except Exception as e:
            print(f"Failed to extract frame background color for {component.name}: {str(e)}")
    
    
    def _extract_text_properties_from_component(self, component: FigmaComponent, settings: Dict[str, Any], color_key: str, prefix: str, mapping: Dict[str, str] = None):
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
                
                # Check if this component has any TEXT children
                has_text = self._has_text_children(node)
                if not has_text:
                    self.add_diagnostic(
                        'warning',
                        'missing_text',
                        component.name,
                        'No TEXT layer found in component',
                        f'In Figma, add a TEXT layer inside "{component.name}" to define font styling.'
                    )
                
                self._extract_text_from_node(node, settings, color_key, prefix, mapping)
                
        except Exception as e:
            self.add_diagnostic(
                'error',
                'api_error',
                component.name,
                f'Failed to fetch component details: {str(e)}',
                'Check your Figma API token and file permissions, or try syncing again.'
            )
    
    def _has_text_children(self, node: Dict) -> bool:
        """Check if a node or its children contain TEXT nodes."""
        if node.get('type') == 'TEXT':
            return True
        if 'children' in node:
            for child in node['children']:
                if self._has_text_children(child):
                    return True
        return False
    
    def _extract_text_from_node(self, node: Dict, settings: Dict[str, Any], color_key: str, prefix: str, mapping: Dict[str, str] = None):
        """Recursively extract text properties from a node and its children."""
        if node.get('type') == 'TEXT':
            # Extract text styles
            text_styles = self._extract_text_styles(node)
            
            # Check for missing font properties
            if not text_styles.get('fontSize'):
                self.add_diagnostic(
                    'warning',
                    'missing_property',
                    node.get('name', 'TEXT node'),
                    'Missing fontSize property',
                    'In Figma, ensure the text layer has a valid font size set.'
                )
            if not text_styles.get('fontFamily'):
                self.add_diagnostic(
                    'warning',
                    'missing_property',
                    node.get('name', 'TEXT node'),
                    'Missing fontFamily property',
                    'In Figma, ensure the text layer has a font family assigned.'
                )
            
            if text_styles.get('color'):
                settings[color_key] = text_styles['color']
            
            if text_styles.get('fontSize') and mapping:
                # Normalize prefix for mapping lookup
                # 'objectType' -> 'object', 'distance' -> 'distance', 'personId' -> stays as is
                mapping_prefix = 'object' if prefix == 'objectType' else prefix.lower()
                
                # Use state-specific property names for size, family, weight
                size_key = f'{mapping_prefix}_text_size'
                family_key = f'{mapping_prefix}_text_family'
                weight_key = f'{mapping_prefix}_text_weight'
                
                if size_key in mapping:
                    settings[mapping[size_key]] = text_styles['fontSize']
                    settings[mapping[family_key]] = text_styles.get('fontFamily', 'Arial')
                    settings[mapping[weight_key]] = text_styles.get('fontWeight', 400)
            elif text_styles.get('fontSize'):
                # Fallback to generic property names
                settings[f'{prefix}TextSize'] = text_styles['fontSize']
                settings[f'{prefix}TextFamily'] = text_styles.get('fontFamily', 'Arial')
                settings[f'{prefix}TextWeight'] = text_styles.get('fontWeight', 400)
        
        # Recursively check children
        if 'children' in node:
            for child in node['children']:
                self._extract_text_from_node(child, settings, color_key, prefix, mapping)

def get_figma_service() -> Optional[FigmaService]:
    """Get configured Figma service instance."""
    api_token = os.getenv('FIGMA_API_TOKEN')
    file_id = os.getenv('FIGMA_FILE_ID')
    
    if not api_token or not file_id:
        raise ValueError("Figma service not configured. Please set FIGMA_API_TOKEN and FIGMA_FILE_ID environment variables.")
    
    return FigmaService(api_token, file_id)
