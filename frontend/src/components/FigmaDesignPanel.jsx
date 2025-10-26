import { useState, useEffect } from "react";
import axios from "axios";
import "./FigmaDesignPanel.css";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000";

export default function FigmaDesignPanel({ onApplyDesign, visualSettings }) {
  const [figmaData, setFigmaData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showMappingTable, setShowMappingTable] = useState(false);
  const [componentMapping, setComponentMapping] = useState({});
  const [warnings, setWarnings] = useState([]);
  
  // Component selection state for flexible mapping
  const [selectedComponents, setSelectedComponents] = useState({
    'Body Tracker': 'body-tracker' // default component name (case-insensitive search)
  });

  // Auto-sync from Figma on component mount
  useEffect(() => {
    syncFromFigma();
  }, []); // Empty dependency array means this runs once on mount

  // Helper function to extract base component name (remove variant suffixes)
  const getBaseComponentName = (fullName) => {
    // Handle Figma variant naming: "ComponentName/Property=Value"
    return fullName.split('/')[0];
  };

  // Helper function to find component case-insensitively
  const findComponent = (componentName, figmaData) => {
    if (!figmaData?.components) return null;
    
    const searchName = getBaseComponentName(componentName);
    
    // First try exact match on base name
    let found = figmaData.components.find(comp => getBaseComponentName(comp.name) === searchName);
    if (found) return found;
    
    // Then try case-insensitive match on base name
    const lowerSearch = searchName.toLowerCase();
    found = figmaData.components.find(comp => getBaseComponentName(comp.name).toLowerCase() === lowerSearch);
    if (found) return found;
    
    // Finally try partial match (contains)
    return figmaData.components.find(comp => 
      getBaseComponentName(comp.name).toLowerCase().includes(lowerSearch) || 
      lowerSearch.includes(getBaseComponentName(comp.name).toLowerCase())
    );
  };

  // Helper function to get available variants for a component
  const getComponentVariants = (componentName, figmaData) => {
    if (!componentName) {
      return [];
    }
    
    const baseName = getBaseComponentName(componentName);
    
    // Special handling for body-tracker - use dedicated body_tracker data
    if (baseName.toLowerCase() === 'body-tracker' && figmaData?.body_tracker?.variants) {
      const variants = Object.keys(figmaData.body_tracker.variants);
      return variants;
    }
    
    // For other components, search through components array
    if (!figmaData?.components) {
      return [];
    }
    
    // Collect all variants for this base component
    const variants = new Set();
    
    figmaData.components.forEach(comp => {
      const compBaseName = getBaseComponentName(comp.name);
      
      if (compBaseName.toLowerCase() === baseName.toLowerCase()) {
        // Check if this component has variant suffix (ComponentName/Property=Value)
        if (comp.name.includes('/')) {
          const variantPart = comp.name.split('/')[1]; // "State=charging"
          if (variantPart && variantPart.includes('=')) {
            const variantValue = variantPart.split('=')[1]; // "charging"
            variants.add(variantValue);
          }
        }
        
        // Also check for direct variants property
        if (comp.variants && Object.keys(comp.variants).length > 0) {
          Object.keys(comp.variants).forEach(v => variants.add(v));
        }
      }
    });
    
    const variantArray = Array.from(variants);
    return variantArray;
  };

  // Define person box groups for simplified mapping
  const personBoxGroups = {
          'Locked/Targeted Person Box': {
            icon: '🔒',
            description: 'Green box when person is in crosshair',
            figmaComponent: 'person-box-locked',
            properties: [
              // Main Frame
              'personLockedBoxColor',
              'personLockedBoxStrokeWidth', 
              'personLockedBoxBorderRadius',
              'personLockedBoxBackgroundColor',
              'personLockedBoxBackgroundOpacity',
              // ID Section
              'personIdLockedTextColor',
              'personIdTextSize',
              'personIdTextFamily',
              'personIdTextWeight',
              'personIdLockedBackgroundColor',
              'personIdLockedBackgroundOpacity',
              // Object Type Section
              'objectTypeLockedTextColor',
              'objectTypeLockedTextSize',
              'objectTypeLockedTextFamily',
              'objectTypeLockedTextWeight',
              'objectTypeLockedBackgroundColor',
              'objectTypeLockedBackgroundOpacity',
              // Distance Section
              'distanceLockedTextColor',
              'distanceLockedTextSize',
              'distanceLockedTextFamily',
              'distanceLockedTextWeight',
              'distanceLockedBackgroundColor',
              'distanceLockedBackgroundOpacity'
            ]
          },
          'Default Person Box': {
            icon: '📦',
            description: 'White box for detected persons',
            figmaComponent: 'person-box-unlocked',
            properties: [
              // Main Frame
              'personUnlockedBoxColor',
              'personUnlockedBoxStrokeWidth',
              'personUnlockedBoxBorderRadius', 
              'personUnlockedBoxBackgroundColor',
              'personUnlockedBoxBackgroundOpacity',
              // ID Section
              'personIdTextColor',
              'personIdTextSize',
              'personIdTextFamily',
              'personIdTextWeight',
              'personIdBackgroundColor',
              'personIdBackgroundOpacity',
              // Object Type Section
              'objectTypeTextColor',
              'objectTypeTextSize',
              'objectTypeTextFamily',
              'objectTypeTextWeight',
              'objectTypeBackgroundColor',
              'objectTypeBackgroundOpacity',
              // Distance Section
              'distanceTextColor',
              'distanceTextSize',
              'distanceTextFamily',
              'distanceTextWeight',
              'distanceBackgroundColor',
              'distanceBackgroundOpacity'
            ]
          },
          'Far Distance Person Box': {
            icon: '🔴',
            description: 'Red box when person is too far away',
            figmaComponent: 'person-box-far',
            properties: [
              // Main Frame
              'personFarBoxColor',
              'personFarBoxStrokeWidth',
              'personFarBoxBorderRadius',
              'personFarBoxBackgroundColor', 
              'personFarBoxBackgroundOpacity',
              // ID Section
              'personIdFarTextColor',
              'personIdTextSize',
              'personIdTextFamily',
              'personIdTextWeight',
              'personIdFarBackgroundColor',
              'personIdFarBackgroundOpacity',
              // Object Type Section
              'objectTypeFarTextColor',
              'objectTypeFarTextSize',
              'objectTypeFarTextFamily',
              'objectTypeFarTextWeight',
              'objectTypeFarBackgroundColor',
              'objectTypeFarBackgroundOpacity',
              // Distance Section
              'distanceFarTextColor',
              'distanceFarTextSize',
              'distanceFarTextFamily',
              'distanceFarTextWeight',
              'distanceFarBackgroundColor',
              'distanceFarBackgroundOpacity'
            ]
          },
          'Background Person Box': {
            icon: '⚫',
            description: 'Grey box for non-priority persons',
            figmaComponent: 'person-box-grey',
            properties: [
              // Main Frame
              'personGreyColor',
              'personGreyStrokeWidth',
              'personGreyBorderRadius',
              'personGreyBackgroundColor',
              'personGreyBackgroundOpacity',
              // ID Section
              'personIdGreyTextColor',
              'personIdTextSize',
              'personIdTextFamily',
              'personIdTextWeight',
              'personIdGreyBackgroundColor',
              'personIdGreyBackgroundOpacity',
              // Object Type Section
              'objectTypeGreyTextColor',
              'objectTypeGreyTextSize',
              'objectTypeGreyTextFamily',
              'objectTypeGreyTextWeight',
              'objectTypeGreyBackgroundColor',
              'objectTypeGreyBackgroundOpacity',
              // Distance Section
              'distanceGreyTextColor',
              'distanceGreyTextSize',
              'distanceGreyTextFamily',
              'distanceGreyTextWeight',
              'distanceGreyBackgroundColor',
              'distanceGreyBackgroundOpacity'
            ]
          },
          'Crosshair': {
            icon: '🎯',
            description: 'Crosshair overlay (default and active states)',
            figmaComponent: 'crosshair',
            properties: [
              'crosshairDefaultImage',
              'crosshairActiveImage'
            ],
            isCrosshair: true  // Special flag to handle differently
          },
          'Body Tracker': {
            icon: '🔘',
            description: 'Body tracking indicator with charging states (5-second timer)',
            figmaComponent: 'body-tracker',
            properties: [
              'bodyTrackerCharging',
              'bodyTrackerReady'
            ],
            isBodyTracker: true  // Special flag for variant-based component
          }
  };

        // Property labels for display
        const propertyLabels = {
          'personLockedBoxColor': 'Border Color',
          'personLockedBoxStrokeWidth': 'Border Width',
          'personLockedBoxBorderRadius': 'Border Radius', 
          'personLockedBoxBackgroundColor': 'Fill Color',
          'personLockedBoxBackgroundOpacity': 'Fill Opacity',
          'personIdLockedTextColor': 'ID Text Color',
          'personIdFarTextColor': 'ID Text Color',
          'personIdGreyTextColor': 'ID Text Color',
          'personIdTextSize': 'ID Text Size',
          'personIdTextFamily': 'ID Text Font',
          'personIdTextWeight': 'ID Text Weight',
          'distanceTextColor': 'Distance Text Color',
          'distanceTextSize': 'Distance Text Size',
          'distanceTextFamily': 'Distance Text Font',
          'distanceTextWeight': 'Distance Text Weight',
          'objectTypeTextColor': 'Object Text Color',
          'objectTypeTextSize': 'Object Text Size',
          'objectTypeTextFamily': 'Object Text Font',
          'objectTypeTextWeight': 'Object Text Weight',
          'personUnlockedBoxColor': 'Border Color',
          'personUnlockedBoxStrokeWidth': 'Border Width',
          'personUnlockedBoxBorderRadius': 'Border Radius',
          'personUnlockedBoxBackgroundColor': 'Fill Color', 
          'personUnlockedBoxBackgroundOpacity': 'Fill Opacity',
          'personIdTextColor': 'ID Text Color',
          'personFarBoxColor': 'Border Color',
          'personFarBoxStrokeWidth': 'Border Width',
          'personFarBoxBorderRadius': 'Border Radius',
          'personFarBoxBackgroundColor': 'Fill Color',
          'personFarBoxBackgroundOpacity': 'Fill Opacity',
          'personGreyColor': 'Border Color',
          'personGreyStrokeWidth': 'Border Width', 
          'personGreyBorderRadius': 'Border Radius',
          'personGreyBackgroundColor': 'Fill Color',
          'personGreyBackgroundOpacity': 'Fill Opacity',
          
          // State-specific text properties
          'distanceLockedTextColor': 'Distance Text Color',
          'distanceLockedTextSize': 'Distance Text Size',
          'distanceLockedTextFamily': 'Distance Text Font',
          'distanceLockedTextWeight': 'Distance Text Weight',
          'objectTypeLockedTextColor': 'Object Text Color',
          'objectTypeLockedTextSize': 'Object Text Size',
          'objectTypeLockedTextFamily': 'Object Text Font',
          'objectTypeLockedTextWeight': 'Object Text Weight',
          'distanceFarTextColor': 'Distance Text Color',
          'distanceFarTextSize': 'Distance Text Size',
          'distanceFarTextFamily': 'Distance Text Font',
          'distanceFarTextWeight': 'Distance Text Weight',
          'objectTypeFarTextColor': 'Object Text Color',
          'objectTypeFarTextSize': 'Object Text Size',
          'objectTypeFarTextFamily': 'Object Text Font',
          'objectTypeFarTextWeight': 'Object Text Weight',
          'distanceGreyTextColor': 'Distance Text Color',
          'distanceGreyTextSize': 'Distance Text Size',
          'distanceGreyTextFamily': 'Distance Text Font',
          'distanceGreyTextWeight': 'Distance Text Weight',
          'objectTypeGreyTextColor': 'Object Text Color',
          'objectTypeGreyTextSize': 'Object Text Size',
          'objectTypeGreyTextFamily': 'Object Text Font',
          'objectTypeGreyTextWeight': 'Object Text Weight',
          
          // Frame background colors
          'objectTypeBackgroundColor': 'Object Background Color',
          'objectTypeBackgroundOpacity': 'Object Background Opacity',
          'objectTypeLockedBackgroundColor': 'Object Background Color',
          'objectTypeLockedBackgroundOpacity': 'Object Background Opacity',
          'objectTypeFarBackgroundColor': 'Object Background Color',
          'objectTypeFarBackgroundOpacity': 'Object Background Opacity',
          'objectTypeGreyBackgroundColor': 'Object Background Color',
          'objectTypeGreyBackgroundOpacity': 'Object Background Opacity',
          'distanceBackgroundColor': 'Distance Background Color',
          'distanceBackgroundOpacity': 'Distance Background Opacity',
          'distanceLockedBackgroundColor': 'Distance Background Color',
          'distanceLockedBackgroundOpacity': 'Distance Background Opacity',
          'distanceFarBackgroundColor': 'Distance Background Color',
          'distanceFarBackgroundOpacity': 'Distance Background Opacity',
          'distanceGreyBackgroundColor': 'Distance Background Color',
          'distanceGreyBackgroundOpacity': 'Distance Background Opacity',
          
          // ID background colors
          'personIdBackgroundColor': 'ID Background Color',
          'personIdBackgroundOpacity': 'ID Background Opacity',
          'personIdLockedBackgroundColor': 'ID Background Color',
          'personIdLockedBackgroundOpacity': 'ID Background Opacity',
          'personIdFarBackgroundColor': 'ID Background Color',
          'personIdFarBackgroundOpacity': 'ID Background Opacity',
          'personIdGreyBackgroundColor': 'ID Background Color',
          'personIdGreyBackgroundOpacity': 'ID Background Opacity',
          
          // Crosshair images
          'crosshairDefaultImage': 'Default State Image',
          'crosshairActiveImage': 'Active State Image',
          
          // Body Tracker variants
          'bodyTrackerCharging': 'Charging State (0-5 sec)',
          'bodyTrackerReady': 'Ready State (5+ sec)'
        };

  // Initialize component mapping with auto-detection
  const initializeComponentMapping = () => {
    if (!figmaData?.components) return {};
    
    const mapping = {};
    
    // Initialize Body Tracker with default variant mapping
    if (figmaData?.body_tracker?.variants) {
      mapping['Body Tracker'] = {
        charging: 'charging',
        ready: 'ready'
      };
    }
    
    // Auto-map person box groups
    Object.entries(personBoxGroups).forEach(([groupName, groupData]) => {
      const matchingComponent = figmaData.components.find(comp => 
        comp.name.toLowerCase().includes(groupData.figmaComponent)
      );
      
      if (matchingComponent) {
        mapping[groupName] = matchingComponent.id;
      }
    });
    
    return mapping;
  };

  // Get current values for a property from Figma data
    const getCurrentValue = (property, componentId, groupData) => {
      // Handle crosshair images specially
      if (groupData?.isCrosshair) {
        if (property === 'crosshairDefaultImage') {
          const hasImage = figmaData?.crosshair_images?.default;
          return { 
            value: hasImage ? 'Loaded from Figma' : 'Not set', 
            isMissing: !hasImage 
          };
        }
        if (property === 'crosshairActiveImage') {
          const hasImage = figmaData?.crosshair_images?.active;
          return { 
            value: hasImage ? 'Loaded from Figma' : 'Not set', 
            isMissing: !hasImage 
          };
        }
      }
      
      // Handle body tracker variants specially
      if (groupData?.isBodyTracker) {
        const bodyTrackerMapping = componentMapping['Body Tracker'] || { charging: 'charging', ready: 'ready' };
        
        if (property === 'bodyTrackerCharging') {
          const variantName = bodyTrackerMapping.charging;
          const hasVariant = variantName && figmaData?.body_tracker?.variants?.[variantName];
          return { 
            value: hasVariant ? `Variant: ${variantName}` : 'Not set', 
            isMissing: !hasVariant 
          };
        }
        if (property === 'bodyTrackerReady') {
          const variantName = bodyTrackerMapping.ready;
          const hasVariant = variantName && figmaData?.body_tracker?.variants?.[variantName];
          return { 
            value: hasVariant ? `Variant: ${variantName}` : 'Not set', 
            isMissing: !hasVariant 
          };
        }
      }
    
    if (!componentId || !figmaData?.components) {
      return { value: visualSettings[property] || 'Not set', isMissing: true };
    }
    
    const component = figmaData.components.find(comp => comp.id === componentId);
    if (!component?.styles) return { value: 'Not available', isMissing: true };
    
    const styles = component.styles;
    let value = null;
    let isMissing = false;
    
    // For text properties, use the global visual settings from the backend
    // since they are extracted from child components and stored globally
    if (property.includes('Text')) {
      value = figmaData.visual_settings?.[property];
      if (!value) {
        value = visualSettings[property] || 'Not available';
        isMissing = true;
      }
      return { value, isMissing };
    }
    
    // For frame background colors (objectType/distance/personId BackgroundColor), use global visual settings
    if ((property.includes('objectType') && property.includes('BackgroundColor')) ||
        (property.includes('distance') && property.includes('BackgroundColor')) ||
        (property.includes('personId') && property.includes('BackgroundColor'))) {
      value = figmaData.visual_settings?.[property];
      if (!value) {
        value = visualSettings[property] || 'Not available';
        isMissing = true;
      }
      return { value, isMissing };
    }
    
    // For frame background opacity, use global visual settings
    if ((property.includes('objectType') && property.includes('BackgroundOpacity')) ||
        (property.includes('distance') && property.includes('BackgroundOpacity')) ||
        (property.includes('personId') && property.includes('BackgroundOpacity'))) {
      value = figmaData.visual_settings?.[property];
      if (!value && value !== 0) {
        value = visualSettings[property] || 'Not available';
        isMissing = true;
      }
      return { value, isMissing };
    }
    
    // Map box property names to Figma style properties
    if (property.includes('Color') && !property.includes('Background')) {
      value = styles.borderColor || styles.color;
      if (!value) {
        value = 'Not available';
        isMissing = true;
      }
    } else if (property.includes('BackgroundColor')) {
      value = styles.backgroundColor;
      if (!value) {
        value = 'Not available';
        isMissing = true;
      }
    } else if (property.includes('StrokeWidth')) {
      value = styles.borderWidth;
      if (!value && value !== 0) {
        value = 'Not available';
        isMissing = true;
      }
    } else if (property.includes('BorderRadius')) {
      value = styles.borderRadius;
      if (!value && value !== 0) {
        value = 'Not available';
        isMissing = true;
      }
    } else if (property.includes('BackgroundOpacity')) {
      value = styles.backgroundOpacity;
      if (!value && value !== 0) {
        value = 'Not available';
        isMissing = true;
      }
    } else {
      value = 'Not available';
      isMissing = true;
    }
    
    return { value, isMissing };
  };

  // Apply mapped design from selected components
  const applyMappedDesign = () => {
    if (!figmaData?.components) return;
    
    const mappedSettings = {};
    
    // Process each person box group
    Object.entries(personBoxGroups).forEach(([groupName, groupData]) => {
      const componentId = componentMapping[groupName];
      if (!componentId) return;
      
      const component = figmaData.components.find(comp => comp.id === componentId);
      if (!component?.styles) return;
      
      const styles = component.styles;
      
      // Map all properties for this group
      groupData.properties.forEach(property => {
        // For frame background colors and text properties, use global visual settings
        if ((property.includes('objectType') && property.includes('BackgroundColor')) ||
            (property.includes('distance') && property.includes('BackgroundColor')) ||
            (property.includes('personId') && property.includes('BackgroundColor')) ||
            (property.includes('objectType') && property.includes('BackgroundOpacity')) ||
            (property.includes('distance') && property.includes('BackgroundOpacity')) ||
            (property.includes('personId') && property.includes('BackgroundOpacity')) ||
            property.includes('Text')) {
          // Use the extracted values from Figma visual_settings
          const extractedValue = figmaData.visual_settings?.[property];
          if (extractedValue !== undefined) {
            mappedSettings[property] = extractedValue;
          }
        } else if (property.includes('Color') && !property.includes('Background')) {
          mappedSettings[property] = styles.borderColor || styles.color;
        } else if (property.includes('BackgroundColor')) {
          mappedSettings[property] = styles.backgroundColor;
        } else if (property.includes('StrokeWidth')) {
          mappedSettings[property] = styles.borderWidth;
        } else if (property.includes('BorderRadius')) {
          mappedSettings[property] = styles.borderRadius;
        } else if (property.includes('BackgroundOpacity')) {
          mappedSettings[property] = styles.backgroundOpacity || 0.2;
        }
      });
    });
    
      // Include crosshair images and sizes if available
      if (figmaData.crosshair_images) {
        if (figmaData.crosshair_images.default) {
          mappedSettings.crosshairDefaultImage = figmaData.crosshair_images.default;
        }
        if (figmaData.crosshair_images.active) {
          mappedSettings.crosshairActiveImage = figmaData.crosshair_images.active;
        }
        if (figmaData.crosshair_images.defaultSize) {
          mappedSettings.crosshairDefaultSize = figmaData.crosshair_images.defaultSize;
        }
        if (figmaData.crosshair_images.activeSize) {
          mappedSettings.crosshairActiveSize = figmaData.crosshair_images.activeSize;
        }
      }
      
      // Include body tracker variants if available
      const selectedBodyTrackerComponent = selectedComponents['Body Tracker'];
      if (selectedBodyTrackerComponent && figmaData?.components) {
        const bodyTrackerMapping = componentMapping['Body Tracker'];
        
        if (bodyTrackerMapping) {
          const chargingVariant = bodyTrackerMapping.charging;
          const readyVariant = bodyTrackerMapping.ready;
          
          // Find charging variant component
          if (chargingVariant) {
            const chargingComponent = figmaData.components.find(comp => {
              const baseName = getBaseComponentName(comp.name);
              const isMatchingBase = baseName.toLowerCase() === selectedBodyTrackerComponent.toLowerCase();
              
              if (!isMatchingBase) return false;
              
              if (comp.name.includes('/')) {
                const variantPart = comp.name.split('/')[1];
                if (variantPart && variantPart.includes('=')) {
                  const variantValue = variantPart.split('=')[1];
                  return variantValue.toLowerCase() === chargingVariant.toLowerCase();
                }
              }
              
              return comp.variants && comp.variants[chargingVariant];
            });
            
            if (chargingComponent) {
              // Extract ALL properties for charging state
              mappedSettings.bodyTrackerChargingProperties = {
                ...chargingComponent.properties,
                ...chargingComponent.styles,
                ...chargingComponent.fills,
                ...chargingComponent.strokes,
                ...chargingComponent.effects,
                ...chargingComponent.layout,
                width: chargingComponent.width || chargingComponent.absoluteBoundingBox?.width,
                height: chargingComponent.height || chargingComponent.absoluteBoundingBox?.height,
                backgroundColor: chargingComponent.backgroundColor,
                fillColor: chargingComponent.fillColor || chargingComponent.fills?.[0]?.color,
                strokeColor: chargingComponent.strokeColor || chargingComponent.strokes?.[0]?.color,
                borderRadius: chargingComponent.cornerRadius || chargingComponent.rectangleCornerRadii?.[0],
                borderWidth: chargingComponent.strokeWeight || chargingComponent.borderWidth,
                fontSize: chargingComponent.fontSize,
                fontFamily: chargingComponent.fontFamily,
                fontWeight: chargingComponent.fontWeight,
                componentType: chargingComponent.type,
                componentName: chargingComponent.name,
                ...Object.fromEntries(
                  Object.entries(chargingComponent).filter(([key, value]) => 
                    typeof value !== 'object' && 
                    typeof value !== 'function' &&
                    !['id', 'parent', 'children'].includes(key)
                  )
                )
              };
              
              // Remove undefined/null values
              mappedSettings.bodyTrackerChargingProperties = Object.fromEntries(
                Object.entries(mappedSettings.bodyTrackerChargingProperties).filter(([key, value]) => 
                  value !== undefined && value !== null && value !== ''
                )
              );
              
              if (chargingComponent.variants && chargingComponent.variants[chargingVariant]) {
                const variantProps = chargingComponent.variants[chargingVariant];
                mappedSettings.bodyTrackerChargingProperties = {
                  ...mappedSettings.bodyTrackerChargingProperties,
                  ...variantProps.properties,
                  ...variantProps.styles,
                  ...variantProps
                };
              }
            }
          }
          
          // Find ready variant component
          if (readyVariant) {
            const readyComponent = figmaData.components.find(comp => {
              const baseName = getBaseComponentName(comp.name);
              const isMatchingBase = baseName.toLowerCase() === selectedBodyTrackerComponent.toLowerCase();
              
              if (!isMatchingBase) return false;
              
              if (comp.name.includes('/')) {
                const variantPart = comp.name.split('/')[1];
                if (variantPart && variantPart.includes('=')) {
                  const variantValue = variantPart.split('=')[1];
                  return variantValue.toLowerCase() === readyVariant.toLowerCase();
                }
              }
              
              return comp.variants && comp.variants[readyVariant];
            });
            
            if (readyComponent) {
              // Extract ALL properties for ready state
              mappedSettings.bodyTrackerReadyProperties = {
                ...readyComponent.properties,
                ...readyComponent.styles,
                ...readyComponent.fills,
                ...readyComponent.strokes,
                ...readyComponent.effects,
                ...readyComponent.layout,
                width: readyComponent.width || readyComponent.absoluteBoundingBox?.width,
                height: readyComponent.height || readyComponent.absoluteBoundingBox?.height,
                backgroundColor: readyComponent.backgroundColor,
                fillColor: readyComponent.fillColor || readyComponent.fills?.[0]?.color,
                strokeColor: readyComponent.strokeColor || readyComponent.strokes?.[0]?.color,
                borderRadius: readyComponent.cornerRadius || readyComponent.rectangleCornerRadii?.[0],
                borderWidth: readyComponent.strokeWeight || readyComponent.borderWidth,
                fontSize: readyComponent.fontSize,
                fontFamily: readyComponent.fontFamily,
                fontWeight: readyComponent.fontWeight,
                componentType: readyComponent.type,
                componentName: readyComponent.name,
                ...Object.fromEntries(
                  Object.entries(readyComponent).filter(([key, value]) => 
                    typeof value !== 'object' && 
                    typeof value !== 'function' &&
                    !['id', 'parent', 'children'].includes(key)
                  )
                )
              };
              
              // Remove undefined/null values
              mappedSettings.bodyTrackerReadyProperties = Object.fromEntries(
                Object.entries(mappedSettings.bodyTrackerReadyProperties).filter(([key, value]) => 
                  value !== undefined && value !== null && value !== ''
                )
              );
              
              if (readyComponent.variants && readyComponent.variants[readyVariant]) {
                const variantProps = readyComponent.variants[readyVariant];
                mappedSettings.bodyTrackerReadyProperties = {
                  ...mappedSettings.bodyTrackerReadyProperties,
                  ...variantProps.properties,
                  ...variantProps.styles,
                  ...variantProps
                };
              }
            }
          }
        }
      }
    
    // Apply the mapped settings directly to the video
    onApplyDesign(mappedSettings, true);
  };

  // Sync from Figma
  const syncFromFigma = async () => {
    setIsLoading(true);
    setError(null);
    setWarnings([]);
    
    try {
      const response = await axios.post(`${API}/api/figma/sync`);
      
      if (response.data.status === 'success') {
        // The response structure includes components and visual_settings at the top level
        const figmaResponseData = {
          status: 'success',
          components: response.data.components || [],
          visual_settings: response.data.visual_settings || {},
          message: response.data.message
        };
        
        // Extract and store warnings
        const syncWarnings = response.data.warnings || [];
        setWarnings(syncWarnings);
        
        // Extract crosshair images
        figmaResponseData.crosshair_images = response.data.crosshair_images || { default: null, active: null };
        
        setFigmaData(figmaResponseData);
        
        // Auto-detect and set Body Tracker component if available
        if (figmaResponseData.components) {
          const bodyTrackerComponent = findComponent('body-tracker', figmaResponseData);
          if (bodyTrackerComponent) {
            setSelectedComponents(prev => ({
              ...prev,
              'Body Tracker': bodyTrackerComponent.name
            }));
            
            // Auto-map variants if they match expected names
            const variants = Object.keys(bodyTrackerComponent.variants || {});
            const chargingVariant = variants.find(v => v.toLowerCase().includes('charging')) || '';
            const readyVariant = variants.find(v => v.toLowerCase().includes('ready')) || '';
            
            if (chargingVariant || readyVariant) {
              setComponentMapping(prev => ({
                ...prev,
                'Body Tracker': {
                  charging: chargingVariant,
                  ready: readyVariant
                }
              }));
            }
          }
        }
        
        setShowMappingTable(true);
      } else {
        setError(response.data.message || 'Failed to sync from Figma');
      }
    } catch (err) {
      console.error('Figma sync error:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to sync from Figma');
    } finally {
      setIsLoading(false);
    }
  };

  // Load cached designs from backend
  const loadCachedDesigns = async () => {
    try {
      const response = await axios.get(`${API}/api/figma/designs`);
      
      if (response.data.status === 'success') {
        // The cached data has a nested structure: response.data.data contains the actual figma data
        const cachedData = response.data.data;
        setFigmaData(cachedData);
      }
    } catch (err) {
      // No cached designs found - this is not an error, just means user needs to sync
    }
  };

  // Load cached Figma data on component mount
  useEffect(() => {
    loadCachedDesigns();
  }, []);

  // Auto-initialize mapping when figma data loads
  useEffect(() => {
    if (figmaData?.components && Object.keys(componentMapping).length === 0) {
      const autoMapping = initializeComponentMapping();
      setComponentMapping(autoMapping);
    }
  }, [figmaData]);

  return (
    <div className="figma-design-panel">
      {/* Header */}
      <div className="figma-panel-header">
        <h3 className="figma-panel-title">🎨 Figma Design Integration</h3>
        <div className="figma-panel-actions">
          <button 
            className={`lcars-btn figma-mapping-toggle ${showMappingTable ? 'active' : ''}`}
            onClick={() => setShowMappingTable(!showMappingTable)}
            disabled={!figmaData}
          >
            {showMappingTable ? 'Hide Mapping' : 'Show Mapping'}
          </button>
          <button 
            className={`lcars-btn figma-sync-btn ${isLoading ? 'syncing' : ''}`}
            onClick={syncFromFigma}
            disabled={isLoading}
          >
            {isLoading ? 'Syncing...' : '🔄 Sync from Figma'}
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="figma-error-message">
          ❌ {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="figma-loading-state">
          <div className="figma-loading-spinner"></div>
          <div className="figma-loading-text">Syncing with Figma...</div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !figmaData && !error && (
        <div className="figma-empty-state">
          <div className="figma-empty-icon">🎨</div>
          <div className="figma-empty-title">No Figma Designs</div>
          <div className="figma-empty-description">
            Click "Sync from Figma" to fetch your latest designs and start mapping them to visual elements.
          </div>
        </div>
      )}

      {/* Content */}
      {!isLoading && figmaData && (
        <div className="figma-content">
          {/* Status Message */}
          <div className="figma-status-message">
            ✅ Found {figmaData.components?.length || 0} components | {Object.keys(componentMapping).length} auto-mapped
            {figmaData.crosshair_images?.default && ' | ✓ Crosshair-Default'}
            {figmaData.crosshair_images?.active && ' | ✓ Crosshair-Active'}
            {(() => {
              const selectedBodyTracker = selectedComponents['Body Tracker'];
              const bodyTrackerComponent = selectedBodyTracker ? findComponent(selectedBodyTracker, figmaData) : null;
              const bodyTrackerMapping = componentMapping['Body Tracker'];
              
              if (bodyTrackerComponent && bodyTrackerMapping) {
                const chargingVariant = bodyTrackerMapping.charging;
                const readyVariant = bodyTrackerMapping.ready;
                let status = '';
                
                if (chargingVariant && bodyTrackerComponent.variants?.[chargingVariant]) {
                  status += ` | ✓ Body-Tracker-${chargingVariant}`;
                }
                if (readyVariant && bodyTrackerComponent.variants?.[readyVariant]) {
                  status += ` | ✓ Body-Tracker-${readyVariant}`;
                }
                
                return status;
              }
              return '';
            })()}
          </div>

          {/* Warnings Section */}
          {warnings.length > 0 && (
            <div className="figma-warnings-section">
              <div className="figma-warnings-header">
                ⚠️ Warnings ({warnings.length})
              </div>
              <div className="figma-warnings-list">
                {warnings.map((warning, idx) => (
                  <div key={idx} className={`figma-warning-item figma-warning-${warning.level}`}>
                    <div className="figma-warning-icon">!</div>
                    <div className="figma-warning-content">
                      <div className="figma-warning-title">
                        {warning.component_name}: {warning.message}
                      </div>
                      <div className="figma-warning-suggestion">
                        {warning.suggestion}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Mapping Table */}
          {showMappingTable && (
            <div className="figma-mapping-container">
              <div className="figma-mapping-header">
                <h5 className="figma-mapping-title">
                  📋 Component Mapping Table
                </h5>
              </div>
              
              <div className="figma-mapping-content">
                {Object.entries(personBoxGroups).map(([groupName, groupData]) => (
                  <div key={groupName} className={`figma-element-group figma-group-${groupName.toLowerCase().replace(/\s+/g, '-')}`}>
                    <div className="figma-group-header">
                      <span className="figma-group-icon">{groupData.icon}</span>
                      <div className="figma-group-info">
                        <h4>{groupName}</h4>
                        <p className="figma-group-description">{groupData.description}</p>
                        <p className="figma-component-suggestion">
                          <strong>Suggested Figma Component:</strong> <code>{groupData.figmaComponent}</code>
                        </p>
                      </div>
                    </div>
                    
                    <div className="figma-group-elements">
                      {/* Component Selector */}
                      {!groupData.isCrosshair && !groupData.isBodyTracker && (
                        <div className="figma-component-selection">
                          <label className="figma-selector-label">Select Figma Component:</label>
                          <select
                            className="figma-component-selector"
                            value={componentMapping[groupName] || ''}
                            onChange={(e) => setComponentMapping(prev => ({
                              ...prev,
                              [groupName]: e.target.value
                            }))}
                          >
                            <option value="">No mapping</option>
                            {figmaData.components?.map(component => (
                              <option key={component.id} value={component.id}>
                                {component.name}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      
                      {/* Crosshair Note */}
                      {groupData.isCrosshair && (
                        <div className="figma-component-selection">
                          
                        </div>
                      )}
                      
                      {/* Body Tracker Component and Variant Selectors */}
                      {groupData.isBodyTracker && figmaData?.components && (
                        <div className="figma-component-selection">
                          <p style={{margin: '0 0 12px 0', fontSize: '13px', color: 'var(--muted)'}}>
                            Select Body Tracker component and map variants to states:
                          </p>
                          
                          <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
                            {/* Component Selector */}
                            <div>
                              <label className="figma-selector-label" style={{fontSize: '12px', fontWeight: 'bold'}}>
                                Figma Component:
                              </label>
                              <select
                                className="figma-component-selector"
                                value={selectedComponents['Body Tracker'] || ''}
                                onChange={(e) => {
                                  const newComponent = e.target.value;
                                  setSelectedComponents(prev => ({
                                    ...prev,
                                    'Body Tracker': newComponent
                                  }));
                                  // Reset variant mappings when component changes
                                  setComponentMapping(prev => ({
                                    ...prev,
                                    'Body Tracker': { charging: '', ready: '' }
                                  }));
                                }}
                              >
                                <option value="">Select component...</option>
                                {(() => {
                                  // Group components by base name and show unique base components
                                  const baseComponents = new Map();
                                  
                                  figmaData.components?.forEach(comp => {
                                    const baseName = getBaseComponentName(comp.name);
                                    if (!baseComponents.has(baseName)) {
                                      baseComponents.set(baseName, {
                                        baseName,
                                        variants: [],
                                        hasVariants: false
                                      });
                                    }
                                    
                                    const baseComp = baseComponents.get(baseName);
                                    
                                    // Check if this is a variant (has / in name)
                                    if (comp.name.includes('/')) {
                                      const variantPart = comp.name.split('/')[1]; // "State=charging"
                                      if (variantPart) {
                                        baseComp.variants.push(variantPart);
                                        baseComp.hasVariants = true;
                                      }
                                    }
                                    
                                    // Also check for direct variants property
                                    if (comp.variants && Object.keys(comp.variants).length > 0) {
                                      baseComp.hasVariants = true;
                                      Object.keys(comp.variants).forEach(v => {
                                        if (!baseComp.variants.includes(v)) {
                                          baseComp.variants.push(v);
                                        }
                                      });
                                    }
                                  });
                                  
                                  return Array.from(baseComponents.values()).map(baseComp => (
                                    <option key={baseComp.baseName} value={baseComp.baseName}>
                                      {baseComp.baseName} ({baseComp.variants.length} variants)
                                    </option>
                                  ));
                                })()}
                              </select>
                            </div>

                            {/* Variant Selectors - only show if component is selected */}
                            {selectedComponents['Body Tracker'] && (() => {
                              const selectedComponentName = selectedComponents['Body Tracker'];
                              const availableVariants = getComponentVariants(selectedComponentName, figmaData);
                              
                              if (availableVariants.length > 0) {
                                return (
                                  <>
                                    <div>
                                      <label className="figma-selector-label" style={{fontSize: '12px'}}>
                                        Charging State (0-5 sec):
                                      </label>
                                    <select
                                      className="figma-component-selector"
                                      value={componentMapping['Body Tracker']?.charging || ''}
                                      onChange={(e) => setComponentMapping(prev => ({
                                        ...prev,
                                        'Body Tracker': {
                                          ...prev['Body Tracker'],
                                          charging: e.target.value,
                                          ready: prev['Body Tracker']?.ready || ''
                                        }
                                      }))}
                                    >
                                      <option value="">No mapping</option>
                                      {availableVariants.map(variantName => (
                                        <option key={variantName} value={variantName}>
                                          {variantName}
                                        </option>
                                      ))}
                                    </select>
                                  </div>
                                  
                                  <div>
                                    <label className="figma-selector-label" style={{fontSize: '12px'}}>
                                      Ready State (5+ sec):
                                    </label>
                                    <select
                                      className="figma-component-selector"
                                      value={componentMapping['Body Tracker']?.ready || ''}
                                      onChange={(e) => setComponentMapping(prev => ({
                                        ...prev,
                                        'Body Tracker': {
                                          charging: prev['Body Tracker']?.charging || '',
                                          ready: e.target.value
                                        }
                                      }))}
                                    >
                                      <option value="">No mapping</option>
                                      {availableVariants.map(variantName => (
                                        <option key={variantName} value={variantName}>
                                          {variantName}
                                        </option>
                                      ))}
                                    </select>
                                  </div>
                                </>
                                );
                              } else {
                                return (
                                  <div style={{padding: '12px', backgroundColor: '#ff950020', borderRadius: '4px', border: '1px solid #ff9500'}}>
                                    <p style={{margin: 0, fontSize: '12px', color: '#ff9500'}}>
                                      ⚠️ No variants found for "{selectedComponentName}"
                                    </p>
                                    <p style={{margin: '4px 0 0 0', fontSize: '11px', color: 'var(--muted)'}}>
                                      Make sure your Figma component has variants like "Ready" and "Charging"
                                    </p>
                                  </div>
                                );
                              }
                            })()}
                          </div>
                        </div>
                      )}
                      
                      {/* Property Displays */}
                      {(componentMapping[groupName] || groupData.isCrosshair || groupData.isBodyTracker) && (
                        <div className="figma-property-displays">
                          {(() => {
                            // Group properties by section
                            const sections = [];
                            let currentSection = null;
                            
                            groupData.properties.forEach((property) => {
                              let sectionName = null;
                              let sectionIcon = null;
                              
                              // Determine section
                              if (groupData.isCrosshair) {
                                sectionName = 'Crosshair Images';
                                sectionIcon = '🎯';
                              } else if (property.includes('Box')) {
                                sectionName = 'Main Frame';
                                sectionIcon = '📦';
                              } else if (property.includes('personId')) {
                                sectionName = 'ID Section';
                                sectionIcon = '🆔';
                              } else if (property.includes('objectType')) {
                                sectionName = 'Object Type Section';
                                sectionIcon = '🏷️';
                              } else if (property.includes('distance')) {
                                sectionName = 'Distance Section';
                                sectionIcon = '📏';
                              }
                              
                              // Create new section or add to current
                              if (!currentSection || currentSection.name !== sectionName) {
                                currentSection = {
                                  name: sectionName,
                                  icon: sectionIcon,
                                  properties: []
                                };
                                sections.push(currentSection);
                              }
                              
                              currentSection.properties.push(property);
                            });
                            
                            // Render sections
                            return sections.map((section, sectionIndex) => (
                              <div key={sectionIndex} className="figma-property-section">
                                <div className="figma-section-header">
                                  {section.icon} {section.name}
                                </div>
                                <div className="figma-section-properties">
                                  {section.properties.map((property) => {
                                    const valueData = getCurrentValue(property, componentMapping[groupName], groupData);
                                    const displayValue = typeof valueData === 'object' ? valueData.value : valueData;
                                    const isMissing = typeof valueData === 'object' ? valueData.isMissing : false;
                                    
                                    // Get the actual image for crosshair preview
                                    let crosshairImageSrc = null;
                                    if (groupData.isCrosshair) {
                                      if (property === 'crosshairDefaultImage' && figmaData?.crosshair_images?.default) {
                                        crosshairImageSrc = figmaData.crosshair_images.default;
                                      } else if (property === 'crosshairActiveImage' && figmaData?.crosshair_images?.active) {
                                        crosshairImageSrc = figmaData.crosshair_images.active;
                                      }
                                    }
                                    
                                    // Get body tracker variant properties for preview
                                    let bodyTrackerProperties = null;
                                    if (groupData.isBodyTracker) {
                                      const bodyTrackerMapping = componentMapping['Body Tracker'];
                                      
                                      // Use the dedicated body_tracker data from backend
                                      if (bodyTrackerMapping && figmaData?.body_tracker?.variants) {
                                        let targetVariantName = null;
                                        
                                        if (property === 'bodyTrackerCharging') {
                                          targetVariantName = bodyTrackerMapping.charging;
                                        } else if (property === 'bodyTrackerReady') {
                                          targetVariantName = bodyTrackerMapping.ready;
                                        }
                                        
                                        if (targetVariantName) {
                                          // Get variant data from body_tracker.variants
                                          const variantData = figmaData.body_tracker.variants[targetVariantName];
                                          
                                          if (variantData && variantData.properties) {
                                            // Use the properties extracted by the backend
                                            bodyTrackerProperties = {
                                              ...variantData.properties,
                                              // Include bounds if available
                                              width: variantData.bounds?.width || variantData.properties.width,
                                              height: variantData.bounds?.height || variantData.properties.height,
                                              // Include image if available
                                              image: variantData.image,
                                            };
                                          }
                                        }
                                      }
                                    }
                                    
                                    return (
                                      <div 
                                        key={property} 
                                        className={`figma-property-display ${isMissing ? 'has-warning' : ''} ${groupData.isCrosshair || groupData.isBodyTracker ? 'figma-crosshair-display' : ''}`}
                                      >
                                        <div className="figma-property-label">
                                          {propertyLabels[property]}
                                        </div>
                                        <div className="figma-property-value">
                                          {isMissing && (
                                            <span className="figma-value-missing-indicator">!</span>
                                          )}
                                          {crosshairImageSrc ? (
                                            <div className="figma-crosshair-preview-container">
                                              <img 
                                                src={crosshairImageSrc} 
                                                alt={propertyLabels[property]}
                                                className="figma-crosshair-preview"
                                              />
                                            </div>
                                          ) : bodyTrackerProperties ? (
                                            <div className="figma-body-tracker-properties">
                                              {/* Show meaningful properties only */}
                                              {(() => {
                                                // Filter out unwanted properties
                                                const filteredProps = Object.entries(bodyTrackerProperties).filter(([key, value]) => 
                                                  value !== 'unknown' && 
                                                  value !== undefined && 
                                                  value !== null && 
                                                  value !== '' &&
                                                  !key.includes('componentName') && // Skip internal names
                                                  !key.includes('name') // Skip duplicate names
                                                );
                                                
                                                // Group properties by type
                                                const colorProps = filteredProps.filter(([key]) => 
                                                  key.toLowerCase().includes('color') || key.toLowerCase().includes('fill') || key.toLowerCase().includes('stroke')
                                                );
                                                const sizeProps = filteredProps.filter(([key]) => 
                                                  ['width', 'height', 'borderWidth', 'strokeWeight', 'borderRadius', 'cornerRadius'].includes(key)
                                                );
                                                const typeProps = filteredProps.filter(([key]) => 
                                                  ['componentType', 'type', 'fontSize', 'fontFamily', 'fontWeight'].includes(key)
                                                );
                                                const otherProps = filteredProps.filter(([key]) => 
                                                  !colorProps.some(([k]) => k === key) && 
                                                  !sizeProps.some(([k]) => k === key) && 
                                                  !typeProps.some(([k]) => k === key)
                                                );
                                                
                                                const renderPropertyGroup = (title, props, icon) => (
                                                  props.length > 0 && (
                                                    <div key={title} style={{marginBottom: '8px'}}>
                                                      <div style={{fontSize: '11px', fontWeight: 'bold', color: 'var(--lcars-blue)', marginBottom: '4px'}}>
                                                        {icon} {title}
                                                      </div>
                                                      {props.map(([key, value]) => (
                                                        <div key={key} className="figma-property-row" style={{marginLeft: '12px', marginBottom: '2px'}}>
                                                          <span className="figma-prop-label" style={{fontSize: '10px'}}>{key}:</span>
                                                          {key.toLowerCase().includes('color') || key.toLowerCase().includes('fill') || key.toLowerCase().includes('stroke') ? (
                                                            <>
                                                              <div 
                                                                className="figma-color-preview" 
                                                                style={{ background: value, width: '12px', height: '12px', marginLeft: '4px' }}
                                                              ></div>
                                                              <span className="figma-prop-value" style={{fontSize: '10px'}}>{value}</span>
                                                            </>
                                                          ) : (
                                                            <span className="figma-prop-value" style={{fontSize: '10px'}}>
                                                              {typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value)}
                                                            </span>
                                                          )}
                                                        </div>
                                                      ))}
                                                    </div>
                                                  )
                                                );
                                                
                                                return (
                                                  <>
                                                    {renderPropertyGroup('Colors', colorProps, '🎨')}
                                                    {renderPropertyGroup('Dimensions', sizeProps, '📏')}
                                                    {renderPropertyGroup('Typography', typeProps, '📝')}
                                                    {renderPropertyGroup('Other', otherProps, '⚙️')}
                                                    
                                                    {filteredProps.length === 0 && (
                                                      <div className="figma-property-row">
                                                        <span className="figma-prop-value" style={{color: 'var(--muted)', fontStyle: 'italic', fontSize: '11px'}}>
                                                          No meaningful properties found in Figma component
                                                        </span>
                                                      </div>
                                                    )}
                                                  </>
                                                );
                                              })()}
                                              
                                              {/* Collapsible debug info */}
                                              <details style={{marginTop: '8px'}}>
                                                <summary style={{fontSize: '10px', color: '#666', cursor: 'pointer'}}>
                                                  🔍 Debug Info (click to expand)
                                                </summary>
                                                <div style={{marginTop: '4px', padding: '4px', backgroundColor: '#f0f0f0', borderRadius: '2px', fontSize: '9px', fontFamily: 'monospace', wordBreak: 'break-all'}}>
                                                  {JSON.stringify(bodyTrackerProperties, null, 2)}
                                                </div>
                                              </details>
                                            </div>
                                          ) : (
                                            <>
                                              {property.includes('Color') && !groupData.isCrosshair && !groupData.isBodyTracker && (
                                                <div 
                                                  className="figma-color-preview" 
                                                  style={{ 
                                                    background: displayValue
                                                  }}
                                                ></div>
                                              )}
                                              <span className="figma-value-text">
                                                {displayValue}
                                              </span>
                                            </>
                                          )}
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            ));
                          })()}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="figma-mapping-footer">
                <button 
                  className="lcars-btn figma-apply-btn"
                  onClick={applyMappedDesign}
                  disabled={Object.keys(componentMapping).length === 0}
                >
                  Apply Mapped Design
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}