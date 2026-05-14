import abookingLogo from '../../assets/abooking-logo.png';

export default function AppHeader({ title, brand }) {
  if (brand) {
    return (
      <div className="app-header-title app-header-title--brand">
        <img
          src={abookingLogo}
          alt="Abooking"
          className="app-header-brand"
        />
      </div>
    );
  }
  return (
    <div className="app-header-title">
      {title}
    </div>
  );
}
