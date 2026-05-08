import { ThemeProvider } from 'styled-components';
import { Theme as TypeUITheme } from '@independent-software/typeui/styles/Theme';

export default function MasterTypeUIProvider({ children }) {
  const enterpriseTypeUITheme = {
    ...TypeUITheme,
    background: 'var(--master-bg-base)',
    fontName: 'Avenir Next',
    fontURL: '',
    fontColor: 'var(--master-text-primary)',
    fontSize: 16,
    fontLineHeight: 24,
    normalColor: 'var(--master-bg-card)',
    primaryColor: 'var(--master-accent)',
    secondaryColor: 'var(--master-accent-soft)',
    positiveColor: 'var(--master-positive)',
    negativeColor: 'var(--master-destructive)',
    radius: 16,
    darken: 0.08,
    gutter: 0.75,
    transition: {
      duration: 0.2,
    },
  };

  return <ThemeProvider theme={enterpriseTypeUITheme}>{children}</ThemeProvider>;
}
