export const Skeleton = ({ width = '100%', height = 16, radius = 8, style = {} }) => (
  <div style={{
    width,
    height,
    borderRadius: radius,
    background: 'var(--tg-surface)',
    animation: 'skeleton-pulse 1.5s ease-in-out infinite',
    ...style
  }} />
);
