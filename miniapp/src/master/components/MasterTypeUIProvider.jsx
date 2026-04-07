import { ThemeProvider } from 'styled-components';
import { Theme as TypeUITheme } from '@independent-software/typeui/styles/Theme';

export default function MasterTypeUIProvider({ children }) {
  const themeParams = window.Telegram?.WebApp?.themeParams || {};
  const enterpriseTypeUITheme = {
    ...TypeUITheme,
    background: themeParams.bg_color || '#ffffff',
    fontName: 'Avenir Next',
    fontURL: '',
    fontColor: themeParams.text_color || '#1f2937',
    fontSize: 16,
    fontLineHeight: 24,
    normalColor: themeParams.secondary_bg_color || '#f2f3f5',
    primaryColor: themeParams.button_color || '#3390ec',
    secondaryColor: themeParams.text_color || '#1f2937',
    positiveColor: '#31b545',
    negativeColor: themeParams.destructive_text_color || '#e53935',
    radius: 14,
    darken: 0.08,
    gutter: 0.75,
    transition: {
      duration: 0.2,
    },
  };

  return <ThemeProvider theme={enterpriseTypeUITheme}>{children}</ThemeProvider>;
}
