// setting up

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

//Route

app.MapGet("/", () => "Hello World!");

app.Run();