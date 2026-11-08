/** Gato del ícono de la página (mismo dibujo que public/favicon.svg). */
export default function Logo({ size = 32 }: { size?: number }) {
  return <img src={`${import.meta.env.BASE_URL}favicon.svg`} width={size} height={size} alt="" />
}
