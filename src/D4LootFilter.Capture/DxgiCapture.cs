// src/D4LootFilter.Capture/DxgiCapture.cs
using OpenCvSharp;
using Vortice.Direct3D;
using Vortice.Direct3D11;
using Vortice.DXGI;

namespace D4LootFilter.Capture;

public class DxgiCapture : IDisposable
{
    private readonly ID3D11Device _device;
    private readonly ID3D11DeviceContext _context;
    private readonly IDXGIOutputDuplication _duplication;
    private readonly ID3D11Texture2D _stagingTexture;
    private readonly int _width;
    private readonly int _height;

    public DxgiCapture(int adapterIndex = 0, int outputIndex = 0)
    {
        using var factory = DXGI.CreateDXGIFactory1<IDXGIFactory1>();
        factory.EnumAdapters1((uint)adapterIndex, out var adapter);
        using (adapter)
        {
            adapter.EnumOutputs((uint)outputIndex, out var output);
            using var output1 = output.QueryInterface<IDXGIOutput1>();

            D3D11.D3D11CreateDevice(
                adapter,
                DriverType.Unknown,
                DeviceCreationFlags.None,
                new[] { FeatureLevel.Level_11_0 },
                out _device!,
                out _context!
            );

            _duplication = output1.DuplicateOutput(_device);

            var desc = output.Description;
            _width = desc.DesktopCoordinates.Right - desc.DesktopCoordinates.Left;
            _height = desc.DesktopCoordinates.Bottom - desc.DesktopCoordinates.Top;

            output.Dispose();
        }

        var stagingDesc = new Texture2DDescription
        {
            Width = (uint)_width,
            Height = (uint)_height,
            MipLevels = 1,
            ArraySize = 1,
            Format = Format.B8G8R8A8_UNorm,
            SampleDescription = new SampleDescription(1, 0),
            Usage = ResourceUsage.Staging,
            CPUAccessFlags = CpuAccessFlags.Read,
        };
        _stagingTexture = _device.CreateTexture2D(stagingDesc);
    }

    public unsafe Mat? CaptureFrame(int timeoutMs = 100)
    {
        var result = _duplication.AcquireNextFrame((uint)timeoutMs, out _, out var resource);
        if (result.Failure)
            return null;

        try
        {
            using var texture = resource.QueryInterface<ID3D11Texture2D>();
            _context.CopyResource(_stagingTexture, texture);

            _context.Map(_stagingTexture, 0, MapMode.Read, Vortice.Direct3D11.MapFlags.None, out var mapped);
            try
            {
                var mat = new Mat(_height, _width, MatType.CV_8UC4);
                var srcPtr = mapped.DataPointer;
                var dstPtr = mat.Data;
                for (int y = 0; y < _height; y++)
                {
                    var src = srcPtr + y * (int)mapped.RowPitch;
                    var dst = dstPtr + y * _width * 4;
                    Buffer.MemoryCopy((void*)src, (void*)dst, _width * 4, _width * 4);
                }
                return mat;
            }
            finally
            {
                _context.Unmap(_stagingTexture, 0);
            }
        }
        finally
        {
            resource.Dispose();
            _duplication.ReleaseFrame();
        }
    }

    public void Dispose()
    {
        _stagingTexture.Dispose();
        _duplication.Dispose();
        _context.Dispose();
        _device.Dispose();
    }
}
