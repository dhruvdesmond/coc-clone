Shader "COA/Border"
{
    // Territory drawn as colour on the ground -- the thing Rise of Nations is remembered for.
    // _Mask: R = player field, G = enemy field, both blurred 0..1 so the 0.5 contour is a smooth curve.
    Properties
    {
        _Mask ("Territory mask", 2D) = "black" {}
        _PlayerColor ("Player", Color) = (0.25, 0.60, 1.0, 1)
        _EnemyColor ("Enemy", Color) = (1.0, 0.27, 0.20, 1)
        _Fill ("Fill alpha", Range(0, 0.4)) = 0.018
        _Glow ("Inner glow", Range(0, 1)) = 0.26
        _Line ("Line alpha", Range(0, 1)) = 0.92
        _Bloom ("Bloom 0..1 (age advance)", Range(0, 1)) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent-20" "RenderPipeline" = "UniversalPipeline" }
        Pass
        {
            Name "Border"
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            ZTest LEqual
            Cull Off
            Offset -2, -2

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            TEXTURE2D(_Mask); SAMPLER(sampler_Mask);
            CBUFFER_START(UnityPerMaterial)
                float4 _Mask_ST; float4 _PlayerColor; float4 _EnemyColor; float _Fill; float _Glow; float _Line; float _Bloom;
            CBUFFER_END

            struct A { float4 pos : POSITION; float2 uv : TEXCOORD0; };
            struct V { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; float3 wpos : TEXCOORD1; };

            V vert(A i) { V o; o.wpos = TransformObjectToWorld(i.pos.xyz); o.pos = TransformWorldToHClip(o.wpos); o.uv = i.uv; return o; }

            float4 layer(float a, float3 col, float3 wpos)
            {
                float inside = smoothstep(0.47, 0.53, a);
                // crisp frontier line, with a slow travelling shimmer so it reads as alive, not painted
                float band = saturate(1.0 - abs(a - 0.5) / 0.055);
                float shimmer = 0.78 + 0.22 * sin(_Time.y * 1.7 + (wpos.x + wpos.z) * 0.55);
                float glow = inside * saturate(1.0 - (a - 0.5) / 0.34) * _Glow;
                float alpha = saturate(band * _Line * shimmer + glow + inside * (_Fill + _Bloom * 0.10));
                return float4(col + band * 0.35 + _Bloom * 0.25, alpha);
            }

            half4 frag(V i) : SV_Target
            {
                float2 m = SAMPLE_TEXTURE2D(_Mask, sampler_Mask, i.uv).rg;
                float4 p = layer(m.r, _PlayerColor.rgb, i.wpos);
                float4 e = layer(m.g, _EnemyColor.rgb, i.wpos);
                float a = saturate(p.a + e.a);
                float3 c = (p.rgb * p.a + e.rgb * e.a) / max(a, 1e-4);
                return half4(c, a);
            }
            ENDHLSL
        }
    }
}
