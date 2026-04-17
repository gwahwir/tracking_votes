/**
 * Mantine cyberpunk theme for Johor Election Monitor
 * Dark background with neon cyan, green, red accents
 */

export const theme = {
  colors: {
    dark: [
      '#c1c2c5', // 0
      '#a6a7ab', // 1
      '#909296', // 2
      '#5c5f66', // 3
      '#373a40', // 4
      '#2c2e33', // 5 — main dark
      '#25262b', // 6
      '#1a1b1e', // 7
      '#0a0a0f', // 8 — darkest (background)
      '#050508', // 9
    ],
    cyan: [
      '#e0f7ff',
      '#b3eeff',
      '#80e5ff',
      '#4ddcff',
      '#1ad3ff',
      '#00cae6', // main cyan
      '#00a8bb',
      '#008694',
      '#006370',
      '#00434a',
    ],
    lime: [
      '#f0fce0',
      '#e1f9cc',
      '#c1f035',
      '#a2e61b',
      '#85db13',
      '#39ff14', // main neon green (MECO)
      '#2cd904',
      '#1fb303',
      '#149d00',
      '#0a8800',
    ],
    red: [
      '#ffe0e0',
      '#ffb3b3',
      '#ff8080',
      '#ff4d4d',
      '#ff1a1a',
      '#ff3131', // main neon red
      '#e6001a',
      '#cc0014',
      '#b3000d',
      '#800008',
    ],
  },
  primaryColor: 'cyan',
  primaryShade: 5,
  fontFamily: "'JetBrains Mono', 'Courier New', monospace",
  fontFamilyMonospace: "'JetBrains Mono', 'Courier New', monospace",
  headings: {
    fontFamily: "'JetBrains Mono', 'Courier New', monospace",
    fontWeight: 700,
  },
  components: {
    Card: {
      defaultProps: {
        p: 'md',
      },
      styles: {
        root: {
          backgroundColor: '#1a1b1e',
          borderColor: '#373a40',
          borderWidth: 1,
        },
      },
    },
    Button: {
      defaultProps: {
        variant: 'filled',
      },
      styles: {
        root: {
          fontFamily: "'JetBrains Mono', 'Courier New', monospace",
        },
      },
    },
    Badge: {
      defaultProps: {
        variant: 'light',
      },
    },
    Modal: {
      styles: {
        content: {
          backgroundColor: '#0a0a0f',
          borderColor: '#373a40',
        },
        header: {
          backgroundColor: '#0a0a0f',
          borderColor: '#373a40',
        },
        title: {
          color: '#00d4ff',
          fontWeight: 700,
        },
      },
    },
    Tabs: {
      styles: {
        tabLabel: {
          fontFamily: "'JetBrains Mono', 'Courier New', monospace",
        },
      },
    },
  },
}

/**
 * Party colour mapping for seat predictions
 */
export const PARTY_COLORS = {
  'BN': '#3366cc',      // Blue
  'UMNO': '#3366cc',    // Blue (same as BN)
  'DAP': '#33cc33',     // Green
  'PKR': '#ff6633',     // Orange
  'PN': '#ff3333',      // Red
  'PAS': '#00aa00',     // Dark Green
  'Amanah': '#ffcc00',  // Yellow
  'Bersatu': '#990000', // Dark Red
  'Independent': '#999999', // Gray
  'No Data': '#666666', // Dark Gray
}

/**
 * Confidence colour mapping
 */
export const CONFIDENCE_COLORS = {
  strong: '#39ff14',   // Neon green (70-100%)
  moderate: '#ffcc00', // Amber (40-69%)
  weak: '#ff3131',     // Neon red (0-39%)
}

/**
 * Confidence ring width by percentage
 */
export const getConfidenceRing = (confidence) => {
  if (confidence >= 70) return { color: CONFIDENCE_COLORS.strong, weight: 4 }
  if (confidence >= 40) return { color: CONFIDENCE_COLORS.moderate, weight: 3 }
  return { color: CONFIDENCE_COLORS.weak, weight: 2 }
}
