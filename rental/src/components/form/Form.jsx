const Form = ({ onSubmit, children, className }) => {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(event);
      }}
      className={` ${className}`}
    >
      {children}
    </form>
  );
};

export default Form;
