import { useEffect } from 'react';
import { buildPatternCssUrl } from './patternData';

/**
 * Sets the --master-pattern CSS variable on document.body based on the
 * master's selected categories. The CSS in theme.css consumes this var
 * inside .master-shell::after as mask-image. When the variable is unset
 * or value is `none`, no pattern is rendered.
 *
 * @param {Array<{slug: string}>} categories - master's selected categories,
 *   typically from useQuery(['master-me-categories']).data?.categories
 */
export function useMasterPattern(categories) {
  // Use a stable key so the effect doesn't re-run on identical slug lists.
  const slugs = (categories || []).map((c) => c.slug).filter(Boolean);
  const key = slugs.join('|');

  useEffect(() => {
    const url = buildPatternCssUrl(slugs);
    if (url) {
      document.body.style.setProperty('--master-pattern', url);
    } else {
      document.body.style.removeProperty('--master-pattern');
    }
    return () => {
      document.body.style.removeProperty('--master-pattern');
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}
