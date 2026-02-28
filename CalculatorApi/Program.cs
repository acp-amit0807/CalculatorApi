var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/calculate", (double num1, double num2, string operation) =>
{
    return operation switch
    {
        "+" => Results.Ok(num1 + num2),
        "-" => Results.Ok(num1 - num2),
        "*" => Results.Ok(num1 * num2),
        "/" when num2 != 0 => Results.Ok(num1 / num2),
        "/" => Results.BadRequest("Cannot divide by zero"),
        _ => Results.BadRequest("Invalid operator")
    };
});
app.Run();
