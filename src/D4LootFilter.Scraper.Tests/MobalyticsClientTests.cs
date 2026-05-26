using System.Net;
using System.Text;

namespace D4LootFilter.Scraper.Tests;

public class MobalyticsClientTests
{
    [Fact]
    public async Task FetchBuildAsync_SuccessfulResponse_ReturnsJson()
    {
        var expectedJson = """{"data":{"game":{"documents":{"userGeneratedDocumentBySlug":{"error":null,"data":{"id":"test"}}}}}}""";
        var handler = new FakeHandler(HttpStatusCode.OK, expectedJson);
        var client = new MobalyticsClient(new HttpClient(handler));

        var result = await client.FetchBuildAsync("test-build");

        Assert.Contains("\"id\":\"test\"", result);
    }

    [Fact]
    public async Task FetchBuildAsync_HttpError_ThrowsHttpRequestException()
    {
        var handler = new FakeHandler(HttpStatusCode.Forbidden, "Blocked");
        var client = new MobalyticsClient(new HttpClient(handler));

        await Assert.ThrowsAsync<HttpRequestException>(() => client.FetchBuildAsync("test-build"));
    }

    [Fact]
    public async Task FetchBuildAsync_SendsCorrectRequest()
    {
        var handler = new FakeHandler(HttpStatusCode.OK, """{"data":{}}""");
        var client = new MobalyticsClient(new HttpClient(handler));

        await client.FetchBuildAsync("my-build-slug");

        Assert.NotNull(handler.LastRequest);
        Assert.Equal(HttpMethod.Post, handler.LastRequest.Method);
        Assert.Equal("https://mobalytics.gg/api/diablo4/v4/graphql/query", handler.LastRequest.RequestUri?.ToString());

        var body = handler.LastRequestBody ?? "";
        Assert.Contains("my-build-slug", body);
        Assert.Contains("Diablo4UgFeaturedDocumentQuery", body);
    }

    [Trait("Category", "Integration")]
    [Fact]
    public async Task FetchBuildAsync_LiveApi_ReturnsValidResponse()
    {
        var client = new MobalyticsClient(new HttpClient());

        var json = await client.FetchBuildAsync("barbarian-whirl-wind-barb");

        Assert.Contains("buildVariants", json);
        Assert.Contains("genericBuilder", json);
    }

    private class FakeHandler : HttpMessageHandler
    {
        private readonly HttpStatusCode _statusCode;
        private readonly string _responseBody;
        public HttpRequestMessage? LastRequest { get; private set; }
        public string? LastRequestBody { get; private set; }

        public FakeHandler(HttpStatusCode statusCode, string responseBody)
        {
            _statusCode = statusCode;
            _responseBody = responseBody;
        }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            LastRequest = request;
            if (request.Content != null)
                LastRequestBody = await request.Content.ReadAsStringAsync(cancellationToken);

            return new HttpResponseMessage(_statusCode)
            {
                Content = new StringContent(_responseBody, Encoding.UTF8, "application/json")
            };
        }
    }
}
