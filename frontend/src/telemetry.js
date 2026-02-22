import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { trace } from '@opentelemetry/api';
import { onLCP, onFID, onCLS, onTTFB, onINP } from 'web-vitals';

const OTEL_COLLECTOR_URL = import.meta.env.VITE_OTEL_COLLECTOR_URL || 'http://localhost:4318';
const SERVICE_NAME = 'frontend';
const SERVICE_VERSION = '1.0.0';


export function initTelemetry() {
  const resource = new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: SERVICE_NAME,
    [SemanticResourceAttributes.SERVICE_VERSION]: SERVICE_VERSION,
    'deployment.environment': import.meta.env.MODE || 'development',
  });

  const provider = new WebTracerProvider({
    resource: resource,
  });

  const exporter = new OTLPTraceExporter({
    url: `${OTEL_COLLECTOR_URL}/v1/traces`,
    headers: {},
  });

  provider.addSpanProcessor(new BatchSpanProcessor(exporter, {
    maxQueueSize: 100,
    maxExportBatchSize: 10,
    scheduledDelayMillis: 500,
  }));

  provider.register({
    contextManager: new ZoneContextManager(),
  });

  // Register auto-instrumentation for fetch and XHR
  registerInstrumentations({
    instrumentations: [
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: [
          /localhost/,  // Local development
          /127\.0\.0\.1/,
          new RegExp(import.meta.env.VITE_API_URL || ''),
        ],
        ignoreUrls: [/otel/, /4318/],
        applyCustomAttributesOnSpan: (span, request, result) => {
          span.setAttribute('http.request.body_size', request.body?.length || 0);
        },
      }),
      
      // Instrument XMLHttpRequest 
      new XMLHttpRequestInstrumentation({
        propagateTraceHeaderCorsUrls: [
          /localhost/,
          /127\.0\.0\.1/,
        ],
        ignoreUrls: [/otel/, /4318/],
      }),
    ],
  });

  console.log('[OpenTelemetry] Browser tracing initialized');
  console.log(`[OpenTelemetry] Sending traces to: ${OTEL_COLLECTOR_URL}`);

  // Initialize Web Vitals reporting
  initWebVitals();

  return trace.getTracer(SERVICE_NAME);
}


function initWebVitals() {
  const tracer = trace.getTracer(SERVICE_NAME);

  const reportVital = (metric) => {
    const span = tracer.startSpan(`web-vital.${metric.name}`, {
      startTime: performance.timeOrigin + metric.startTime,
    });
    
    span.setAttribute('web_vital.name', metric.name);
    span.setAttribute('web_vital.value', metric.value);
    span.setAttribute('web_vital.rating', metric.rating); 
    span.setAttribute('web_vital.id', metric.id);
    
    span.end(performance.timeOrigin + metric.startTime + metric.value);
    
    console.log(`[WebVital] ${metric.name}: ${metric.value.toFixed(2)} (${metric.rating})`);
  };

  // Register callbacks for each Web Vital
  onLCP(reportVital);
  onFID(reportVital);
  onCLS(reportVital);
  onTTFB(reportVital);
  onINP(reportVital);
}


export function startInteractionSpan(name, attributes = {}) {
  const tracer = trace.getTracer(SERVICE_NAME);
  const span = tracer.startSpan(`user.${name}`, {
    attributes: {
      'interaction.type': 'click',
      ...attributes,
    },
  });

  return () => span.end();
}


export async function withSpan(name, attributes, fn) {
  const tracer = trace.getTracer(SERVICE_NAME);
  const span = tracer.startSpan(name, { attributes });
  
  try {
    const result = await fn();
    span.setAttribute('success', true);
    return result;
  } catch (error) {
    span.setAttribute('success', false);
    span.setAttribute('error.message', error.message);
    span.recordException(error);
    throw error;
  } finally {
    span.end();
  }
}