import { ThemeProvider } from 'styled-components';
import { Theme as TypeUITheme } from '@independent-software/typeui/styles/Theme';

const enterpriseTypeUITheme = {
  ...TypeUITheme,
  background: '#eff5f3',
  fontName: 'Avenir Next',
  fontURL: '',
  fontColor: '#102822',
  fontSize: 16,
  fontLineHeight: 24,
  normalColor: '#dce9e6',
  primaryColor: '#0f766e',
  secondaryColor: '#102822',
  positiveColor: '#0f8a55',
  negativeColor: '#b42318',
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
