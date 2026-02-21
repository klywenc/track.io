using Microsoft.AspNetCore.Mvc;
using StackExchange.Redis;
using System.Text.Json;
var builder = WebApplication.CreateBuilder(args);


var redisConn = builder.Configuration.GetConnectionString("Redis") ?? "localhost:6379";
builder.Services.AddSingleton<IConnectionMultiplexer>(ConnectionMultiplexer.Connect(redisConn));
var app = builder.Build();

app.Map("/api/ingest", async (JsonElement payload, IConnectionMultiplexer redis) =>
{
    var db = redis.GetDatabase();
    string jsonString = payload.GetRawText();
    await db.ListLeftPushAsync("raw_bugs_queue", jsonString);
    Console.WriteLine("Blad wrzucony do kolejki");
    return Results.Accepted();
});
app.MapGet("/", () => "API Działa!");
Console.WriteLine("--- ODPALAMY APP.RUN() ---");

app.Run();