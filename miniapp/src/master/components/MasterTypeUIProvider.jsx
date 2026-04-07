import { ThemeProvider } from 'styled-components';
import { Theme as TypeUITheme } from '@independent-software/typeui/styles/Theme';

const enterpriseTypeUITheme = {
  ...TypeUITheme,
  background: '#f2f5fb',
  fontName: 'Avenir Next',
  fontURL: '',
  fontColor: '#12213b',
  fontSize: 16,
  fontLineHeight: 24,
  normalColor: '#dbe4f2',
  primaryColor: '#1f5dcf',
  secondaryColor: '#12213b',
  positiveColor: '#1f8f56',
  negativeColor: '#c62828',
  radius: 14,
  darken: 0.08,
  gutter: 0.75,
  transition: {
    duration: 0.2,
  },
};

export default function MasterTypeUIProvider({ children }) {
  return <ThemeProvider theme={enterpriseTypeUITheme}>{children}</ThemeProvider>;
}
