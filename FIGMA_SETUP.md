# Figma Integration Setup Guide

This guide will help you set up Figma integration for designing custom UI overlays in ProtoCam.

## Prerequisites

1. A Figma account with access to create and edit files
2. Basic understanding of Figma components and frames

## Step 1: Get Your Figma API Token

1. Go to [Figma Settings](https://www.figma.com/settings)
2. Scroll down to "Personal access tokens"
3. Click "Create a new personal access token"
4. Give it a name like "ProtoCam"
5. Copy the generated token (save it securely - you won't see it again!)

## Step 2: Create Your Design File

1. Create a new Figma file for your ProtoCam overlays
2. Name it something like "ProtoCam UI Overlays"
3. Copy the file ID from the URL (e.g., `https://www.figma.com/file/FILE_ID/...`)

## Step 3: Configure Environment Variables

1. Copy `.env.example` to `.env` in your project root
2. Add your credentials:
   ```
   FIGMA_API_TOKEN=your_actual_token_here
   FIGMA_FILE_ID=your_actual_file_id_here
   ```

## Step 4: Design Your Overlay Components

Create components/frames in your Figma file using these naming conventions:

### Bounding Boxes
- **Person boxes**: Include "person" in the name
  - `person-box-locked` - Green box for targeted people
  - `person-box-unlocked` - White box for default people  
  - `person-box-far` - Red box for distant people
  - `person-box-grey` - Grey box for background people

- **Vehicle boxes**: Include "vehicle" in the name
  - `vehicle-box-locked` - Blue box for targeted vehicles
  - `vehicle-box-unlocked` - Yellow box for default vehicles
  - `vehicle-box-far` - Orange box for distant vehicles
  - `vehicle-box-grey` - Grey box for background vehicles

### Crosshairs
- Include "crosshair", "reticle", or "target" in the name
- Examples: `crosshair-taser`, `reticle-circle`, `target-custom`

### Text Labels
- Include "text" or "label" in the name
- Examples: `text-person-id`, `label-distance`, `text-vehicle-locked`

### Tracking Dots
- Include "dot", "marker", or "tracking" in the name
- Examples: `tracking-dot-solid`, `marker-ring`, `dot-custom`

### Design Themes
You can organize components into themes by using folder-like naming:
- `Theme1/person-box-locked`
- `Theme1/crosshair-taser`
- `Theme2/person-box-locked`
- `Theme2/crosshair-hawkeye`

## Step 5: Component Design Tips

### Colors
- Use stroke/border colors for bounding boxes
- Use fill colors for solid elements like dots
- The system will automatically extract colors and convert them to hex

### Sizing
- Crosshair size will be determined by the component's dimensions
- Tracking dot size will be scaled based on component size
- Text size will use the fontSize from text components

### Custom Graphics
- Complex shapes will be exported as SVG for custom crosshairs and tracking dots
- Keep designs simple for better performance

## Step 6: Test Your Integration

1. Start your ProtoCam application [[memory:3490176]]
2. Upload a video and navigate to the Visual Customization panel
3. Click "Sync from Figma" to import your designs
4. Select a design theme to apply it
5. Click "Apply Changes" to see your custom overlays on the video

## Troubleshooting

### "Figma service not configured" Error
- Check that your `.env` file has the correct `FIGMA_API_TOKEN` and `FIGMA_FILE_ID`
- Restart your backend server after adding environment variables

### "No components found" Message
- Verify your component names include the required keywords (person, vehicle, crosshair, etc.)
- Check that your Figma file is accessible with your API token

### Components Not Applying Correctly
- Ensure your components have visible strokes/fills
- Check that component names match the expected patterns
- Use the "Current Figma Settings Preview" to debug what's being imported

## Advanced Usage

### Mode-Specific Designs
Create different designs for each mode by including mode names:
- `taser-crosshair` - Only applies in Taser mode
- `hawkeye-status` - Only applies in Hawkeye mode
- `all-mode-box` - Applies in All mode

### Multiple Design Systems
You can maintain multiple design themes in the same file and switch between them in the app.

## Support

If you encounter issues:
1. Check the browser console for error messages
2. Verify your Figma file permissions
3. Ensure all required components are properly named
4. Test with a simple design first before creating complex overlays
