function PanelHeading({ title, description, action }) {
  return (
    <div className="panel-heading">
      <div><h2>{title}</h2>{description && <p>{description}</p>}</div>
      {action && <div className="panel-action">{action}</div>}
    </div>
  )
}

export default PanelHeading
