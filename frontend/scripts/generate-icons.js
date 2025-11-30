#!/usr/bin/env node
/**
 * PWA Icon Generator Script
 * 
 * This script generates PWA icons from the favicon.svg file.
 * 
 * Requirements:
 *   npm install sharp
 * 
 * Usage:
 *   node scripts/generate-icons.js
 * 
 * Note: For production, replace favicon.svg with your actual logo.
 */

const fs = require('fs');
const path = require('path');

// Check if sharp is available
let sharp;
try {
  sharp = require('sharp');
} catch (e) {
  console.log('sharp module not found. Install with: npm install sharp');
  console.log('');
  console.log('For now, creating placeholder icons...');
  
  // Create simple placeholder PNG files (1x1 blue pixel)
  const sizes = [72, 96, 128, 144, 152, 192, 384, 512];
  const iconsDir = path.join(__dirname, '../public/icons');
  
  if (!fs.existsSync(iconsDir)) {
    fs.mkdirSync(iconsDir, { recursive: true });
  }
  
  // Create a minimal valid PNG (1x1 blue pixel)
  // This is a base64 encoded 1x1 blue PNG
  const bluePNG = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAGA9/OgDQAAAABJRU5ErkJggg==',
    'base64'
  );
  
  sizes.forEach(size => {
    const filename = `icon-${size}x${size}.png`;
    const filepath = path.join(iconsDir, filename);
    fs.writeFileSync(filepath, bluePNG);
    console.log(`Created placeholder: ${filename}`);
  });
  
  // Create apple-touch-icon.png
  fs.writeFileSync(path.join(__dirname, '../public/apple-touch-icon.png'), bluePNG);
  console.log('Created placeholder: apple-touch-icon.png');
  
  console.log('');
  console.log('Note: Replace these placeholders with properly sized icons for production.');
  console.log('You can use tools like https://realfavicongenerator.net/ to generate icons from your logo.');
  
  process.exit(0);
}

// Icon sizes for PWA
const sizes = [72, 96, 128, 144, 152, 192, 384, 512];
const inputSvg = path.join(__dirname, '../public/favicon.svg');
const outputDir = path.join(__dirname, '../public/icons');

async function generateIcons() {
  // Create output directory if it doesn't exist
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  console.log('Generating PWA icons from favicon.svg...');

  for (const size of sizes) {
    const outputPath = path.join(outputDir, `icon-${size}x${size}.png`);
    
    await sharp(inputSvg)
      .resize(size, size)
      .png()
      .toFile(outputPath);
    
    console.log(`Generated: icon-${size}x${size}.png`);
  }

  // Generate apple-touch-icon (180x180)
  await sharp(inputSvg)
    .resize(180, 180)
    .png()
    .toFile(path.join(__dirname, '../public/apple-touch-icon.png'));
  
  console.log('Generated: apple-touch-icon.png');
  console.log('Done!');
}

generateIcons().catch(console.error);
