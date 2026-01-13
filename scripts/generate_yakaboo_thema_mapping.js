#!/usr/bin/env node

/**
 * Generate comprehensive Yakaboo to THEMA mapping from actual category hierarchy
 * Extracts all levels 1-7 and intelligently maps to THEMA codes
 */

const fs = require('fs');
const path = require('path');

// Load data
const yakabooCategories = JSON.parse(
  fs.readFileSync(path.join(__dirname, '../data/yakaboo_categories_tree.json'), 'utf8')
);

// THEMA code mappings by keyword patterns
const themaKeywordMap = {
  // Fiction genres
  fantast: ['FM'],
  fantasy: ['FM'],
  sci.?fi: ['FL'],
  thriller: ['FF'],
  suspense: ['FF'],
  detective: ['FF'],
  crime: ['FF'],
  mystery: ['FF'],
  horror: ['FK'],
  romance: ['FR'],
  adventure: ['FJ'],
  action: ['FJ'],
  biography: ['DN', 'DNBF'],
  autobi: ['DN'],
  memoir: ['DN'],
  classic: ['FC'],
  poetry: ['DC'],
  drama: ['DA'],
  
  // Non-fiction
  business: ['KJ', 'KFF'],
  economk: ['KC'],
  finance: ['KFF'],
  psycholog: ['JM', 'VFX'],
  health: ['VFM', 'MK'],
  fitness: ['WB'],
  nutrition: ['WB'],
  cook: ['WB'],
  culinar: ['WB'],
  art: ['A', 'AB'],
  music: ['AV'],
  cinema: ['AP'],
  film: ['AP'],
  history: ['NH', 'NHD'],
  religion: ['QR'],
  philosophi: ['QD'],
  politic: ['JP'],
  law: ['L', 'LA'],
  computer: ['U', 'UM'],
  programm: ['UM'],
  technolog: ['T'],
  science: ['P', 'PD'],
  physic: ['PH'],
  chemi: ['PN'],
  biolog: ['PS'],
  astronom: ['PG'],
  math: ['PB'],
  travel: ['WH'],
  educat: ['J', 'JN'],
  language: ['CJ'],
  hobby: ['W'],
  craft: ['WF'],
  garden: ['WM'],
  sport: ['WS'],
  self.help: ['VS'],
  development: ['VS'],
  personal: ['VS'],
  motivat: ['VS'],
  children: ['Y', 'YF'],
  kid: ['Y'],
  teen: ['Y'],
  young.adult: ['Y'],
  comic: ['X'],
  graphic: ['X'],
  manga: ['X'],
  esoter: ['VXW'],
  occult: ['VXW'],
};

// Age group to THEMA mapping
const ageGroupMap = {
  '0-3': ['5A'],
  '3-6': ['5A'],
  '6-9': ['5AF'],
  '9-12': ['5AH'],
  '12+': ['5AK'],
  '12-14': ['5AK'],
  '14+': ['5AK'],
  preschool: ['5A'],
  elementary: ['5AF'],
  middle: ['5AH'],
  adult: [],
};

// Language codes
const languageMap = {
  english: 'eng',
  englisch: 'eng',
  english: 'eng',
  ukrainian: 'ukr',
  ukrain: 'ukr',
  russian: 'rus',
  french: 'fra',
  german: 'deu',
  spanish: 'spa',
  italian: 'ita',
  polish: 'pol',
  czech: 'ces',
  hungarian: 'hun',
  portuguese: 'por',
  dutch: 'nld',
  greek: 'ell',
  arabic: 'ara',
  chinese: 'zho',
  japanese: 'jpn',
  korean: 'kor',
  hebrew: 'heb',
  finnish: 'fin',
  swedish: 'swe',
  danish: 'dan',
  norwegian: 'nor',
  latvian: 'lav',
  lithuanian: 'lit',
  estonian: 'est',
  hungarian: 'hun',
  thai: 'tha',
  vietnamese: 'vie',
  hindi: 'hin',
  turkish: 'tur',
  romanian: 'ron',
  serbian: 'srp',
  croatian: 'hrv',
  slovak: 'slk',
  slovenian: 'slv',
  bulgarian: 'bul',
  belarusian: 'bel',
  kazakh: 'kaz',
  georgian: 'kat',
  armenian: 'hye',
  persian: 'fas',
  irish: 'gle',
  latin: 'lat',
  hebrew: 'heb',
  ancient.greek: 'grc',
};

/**
 * Extract THEMA codes from category name using keyword matching
 */
function extractThemaCodes(name) {
  const codes = new Set();
  const lowerName = name.toLowerCase();

  for (const [keyword, themaCodes] of Object.entries(themaKeywordMap)) {
    const regex = new RegExp(keyword, 'i');
    if (regex.test(lowerName)) {
      themaCodes.forEach(code => codes.add(code));
    }
  }

  return Array.from(codes);
}

/**
 * Detect if category is book-related
 */
function isBookCategory(category) {
  const bookKeywords = ['kniga', 'literatur', 'roman', 'povid', 'skazka', 'basni', 'book', 'publishing'];
  const name = category.name.toLowerCase();
  
  // Check if any parent is a book category
  let current = category;
  while (current) {
    if (bookKeywords.some(kw => current.name.toLowerCase().includes(kw))) {
      return true;
    }
    // Check parent
    const parent = yakabooCategories.find(c => c.id === parseInt(current.parent_id));
    current = parent;
  }
  
  return false;
}

/**
 * Build category hierarchy map
 */
function buildHierarchy() {
  const categoryMap = new Map();
  
  yakabooCategories.forEach(cat => {
    categoryMap.set(cat.id, {
      id: cat.id,
      name: cat.name,
      level: cat.level,
      parent_id: cat.parent_id,
      url_path: cat.url_path,
      themaCodes: extractThemaCodes(cat.name),
    });
  });

  return categoryMap;
}

/**
 * Get parent chain for a category
 */
function getParentChain(catId, categoryMap) {
  const chain = [];
  let current = categoryMap.get(catId);
  
  while (current) {
    chain.unshift(current);
    current = categoryMap.get(parseInt(current.parent_id));
  }
  
  return chain;
}

/**
 * Consolidate THEMA codes from parent chain
 */
function consolidateThemaCodes(parentChain) {
  const codes = new Set();
  const importance = new Map();
  
  parentChain.forEach((cat, idx) => {
    // Earlier levels get higher priority
    const weight = parentChain.length - idx;
    cat.themaCodes.forEach(code => {
      if (!importance.has(code)) {
        importance.set(code, weight);
      } else {
        importance.set(code, Math.max(importance.get(code), weight));
      }
      codes.add(code);
    });
  });
  
  // Return sorted by importance
  return Array.from(codes).sort((a, b) => 
    (importance.get(b) || 0) - (importance.get(a) || 0)
  );
}

/**
 * Generate YAML mapping
 */
function generateYamlMapping(categoryMap) {
  let yaml = `# Yakaboo to THEMA Code Mapping (Auto-generated)
# Generated from actual category hierarchy with 7 levels of depth
# Last updated: ${new Date().toISOString().split('T')[0]}

version: "2.0"
description: "Complete Yakaboo category to THEMA mapping (all levels 1-7)"

# Hierarchical categories (grouped by level)
categories:
`;

  // Group by parent and level for better organization
  const bookCategories = Array.from(categoryMap.values())
    .filter(cat => isBookCategory(cat))
    .sort((a, b) => {
      // Sort by level, then by name
      if (a.level !== b.level) return parseInt(a.level) - parseInt(b.level);
      return a.name.localeCompare(b.name);
    });

  let currentLevel = null;
  let currentParent = null;

  bookCategories.forEach((cat, idx) => {
    // Add level comment
    if (cat.level !== currentLevel) {
      currentLevel = cat.level;
      yaml += `\n  # Level ${currentLevel} Categories\n`;
    }

    const themaCodes = cat.themaCodes.length > 0 
      ? cat.themaCodes 
      : extractThemaCodes(cat.name);

    yaml += `
  ${cat.id}:
    name: "${cat.name.replace(/"/g, '\\"')}"
    level: ${cat.level}
    parent_id: ${cat.parent_id}
    thema_codes: ${JSON.stringify(themaCodes)}
    url_path: "${cat.url_path}"
`;
  });

  return yaml;
}

/**
 * Main execution
 */
function main() {
  console.log('🔄 Building category hierarchy...');
  const categoryMap = buildHierarchy();
  console.log(`✓ Loaded ${categoryMap.size} categories`);

  console.log('🔄 Generating THEMA mappings...');
  const yaml = generateYamlMapping(categoryMap);

  const outputPath = path.join(__dirname, '../config/yakaboo_to_thema_mapping_full.yaml');
  fs.writeFileSync(outputPath, yaml);
  
  console.log(`✅ Generated: ${outputPath}`);
  console.log(`   - Total categories: ${categoryMap.size}`);
  console.log(`   - Book categories: ${Array.from(categoryMap.values()).filter(c => isBookCategory(c)).length}`);
  console.log(`   - Max depth level: 7`);
}

main();
