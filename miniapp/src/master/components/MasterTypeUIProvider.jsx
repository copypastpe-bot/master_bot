import { ThemeProvider } from 'styled-components';
import { Theme as TypeUITheme } from '@independent-software/typeui/styles/Theme';

export default function MasterTypeUIProvider({ children }) {
  const themeParams = window.Telegram?.WebApp?.themeParams || {};
  const enterpriseTypeUITheme = {
    ...TypeUITheme,
    background: '#0b1622',
    fontName: 'Avenir Next',
    fontURL: '',
    fontColor: themeParams.text_color || '#f6fbff',
    fontSize: 16,
    fontLineHeight: 24,
    normalColor: 'rgba(23, 35, 52, 0.86)',
    primaryColor: themeParams.button_color || '#4f9cf9',
    secondaryColor: themeParams.accent_text_color || '#7dc1ff',
    positiveColor: '#57d68d',
    negativeColor: themeParams.destructive_text_color || '#ff6f87',
    radius: 16,
    darken: 0.08,
    gutter: 0.75,
    transition: {
      duration: 0.2,
    },
  };

  return <ThemeProvider theme={enterpriseTypeUITheme}>{children}</ThemeProvider>;
}
