# File Processing Endpoint

## Endpoint: `process_file`

Processes files (PDFs/images) and returns comprehensive text descriptions over HTTPS.

**URL:** `POST /upload`

**Command:** `process_file`

---

## Request Format

```javascript
const formData = new FormData();
formData.append('command', 'process_file');
formData.append('fileUrl', 'https://...signed-url...');  // Supabase signed URL
formData.append('fileType', 'pdf');  // or 'image'
formData.append('maxPages', '50');  // Optional: limit pages for large PDFs

const response = await fetch('YOUR_INFERENCE_BACKEND_URL/upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
```

---

## Response Format

### Success Response (200)
```json
{
  "status": "success",
  "textContent": "Full extracted text from PDF...",
  "imageDescriptions": [
    {
      "page": 1,
      "description": "Page 1 contains a title page with...",
      "hasVisualContent": true
    },
    {
      "page": 2,
      "description": "Page 2 shows a diagram of...",
      "hasVisualContent": true
    }
  ],
  "comprehensiveDescription": "DOCUMENT SUMMARY (90 pages)\n\nTEXT CONTENT:\n...\n\nVISUAL CONTENT DESCRIPTIONS:\n...",
  "pageCount": 90
}
```

### Error Response (500)
```json
{
  "status": "error",
  "error": "Failed to download file: Connection timeout",
  "textContent": null,
  "imageDescriptions": [],
  "comprehensiveDescription": null,
  "pageCount": 0
}
```

---

## Reliability Considerations

### ⚠️ Potential Issues

1. **Network Failures**
   - Download timeout (60s default)
   - Connection drops
   - Invalid/expired signed URLs

2. **Processing Failures**
   - Large PDFs (>100 pages) may timeout
   - Memory issues on Render (512MB limit)
   - LLM API rate limits/costs

3. **Race Conditions**
   - Multiple requests for same file
   - File deleted during processing

### ✅ Reliability Improvements

#### 1. **Retry Logic (Primary Backend)**
```javascript
async function processFileWithRetry(fileUrl, fileType, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const result = await callProcessFileEndpoint(fileUrl, fileType);
      if (result.status === 'success') {
        return result;
      }
      // Wait before retry (exponential backoff)
      await sleep(1000 * Math.pow(2, i));
    } catch (error) {
      if (i === maxRetries - 1) throw error;
    }
  }
}
```

#### 2. **Timeout Handling**
- Set reasonable timeout (e.g., 5 minutes for large PDFs)
- Use `maxPages` parameter to limit processing
- Consider async processing for very large files

#### 3. **Error Handling**
```javascript
try {
  const result = await processFile(fileUrl, fileType);
  
  if (result.status === 'error') {
    // Log error
    console.error('Processing failed:', result.error);
    
    // Store partial result or mark as failed
    await updateFileStatus(fileId, 'processing_failed', {
      error: result.error
    });
    
    // Optionally retry later
    await scheduleRetry(fileId);
  } else {
    // Store successful result
    await saveProcessedContent(fileId, result);
  }
} catch (networkError) {
  // Handle network/timeout errors
  await markForRetry(fileId);
}
```

#### 4. **Async Processing Pattern** (More Reliable)
Instead of synchronous HTTP call, consider:

```javascript
// Primary Backend: Queue job
await queueFileProcessing({
  fileId,
  fileUrl,
  fileType
});

// Return immediately
return { status: 'queued', jobId: jobId };

// Worker processes async and updates Prisma when done
```

---

## Best Practices

### 1. **Use maxPages for Large PDFs**
```javascript
// For PDFs > 50 pages, limit processing
const maxPages = fileSize > 50 ? 50 : null;
formData.append('maxPages', maxPages?.toString() || '');
```

### 2. **Handle Timeouts**
```javascript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 min

try {
  const response = await fetch(url, {
    signal: controller.signal,
    // ... other options
  });
} finally {
  clearTimeout(timeoutId);
}
```

### 3. **Store Partial Results**
Even if processing fails, you might get partial text content:
```javascript
if (result.textContent && result.status === 'error') {
  // Save partial result, mark as incomplete
  await savePartialContent(fileId, result.textContent);
}
```

### 4. **Monitor Processing Times**
Track how long processing takes:
- Small PDFs (<20 pages): ~10-30 seconds
- Medium PDFs (20-50 pages): ~30-90 seconds
- Large PDFs (50+ pages): ~90-300+ seconds

---

## Alternative: More Reliable Architecture

If reliability is critical, consider:

### Option A: Webhook Pattern
1. Primary backend calls inference backend
2. Inference backend processes async
3. Inference backend calls webhook when done
4. Primary backend stores result

### Option B: Job Queue (Recommended)
1. Primary backend adds job to queue (Redis/BullMQ)
2. Worker processes files async
3. Worker updates Prisma directly
4. Primary backend polls or uses webhooks

### Option C: Database Polling
1. Primary backend marks file as "processing"
2. Inference backend polls for pending files
3. Processes and updates status
4. Primary backend checks status periodically

---

## Cost Considerations

- **Text extraction**: Free (PyMuPDF)
- **Image descriptions**: ~$0.01-0.05 per page (GPT-4o-mini)
- **90-page PDF**: ~$0.90-4.50 per file

**Optimization**: For large PDFs, sample pages instead of processing all:
- Pages 1-5, then every 10th page, then last 5 pages
- Reduces cost by ~80% while maintaining coverage

---

## Example: Primary Backend Integration

```typescript
// After file upload to Supabase Storage
async function handleFileUpload(fileId: string, fileUrl: string, fileType: string) {
  try {
    // Call inference backend
    const formData = new FormData();
    formData.append('command', 'process_file');
    formData.append('fileUrl', fileUrl);
    formData.append('fileType', fileType);
    
    const response = await fetch(INFERENCE_BACKEND_URL + '/upload', {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(300000) // 5 min timeout
    });
    
    const result = await response.json();
    
    if (result.status === 'success') {
      // Store in Prisma
      await prisma.file.update({
        where: { id: fileId },
        data: {
          processedContent: result.comprehensiveDescription,
          textContent: result.textContent,
          imageDescriptions: result.imageDescriptions,
          processingStatus: 'completed',
          processedAt: new Date()
        }
      });
    } else {
      // Handle error
      await prisma.file.update({
        where: { id: fileId },
        data: {
          processingStatus: 'failed',
          processingError: result.error
        }
      });
      
      // Retry logic here
      await scheduleRetry(fileId);
    }
  } catch (error) {
    // Network/timeout error
    await prisma.file.update({
      where: { id: fileId },
      data: {
        processingStatus: 'pending_retry'
      }
    });
  }
}
```

---

## Summary

**Current Approach (HTTP Return):**
- ✅ Simple to implement
- ✅ Works for small-medium files
- ⚠️ Less reliable for large files/timeouts
- ⚠️ Requires retry logic on primary backend

**Recommended for Production:**
- Use job queue (Redis/BullMQ) for async processing
- Or implement webhook pattern
- Add exponential backoff retries
- Monitor processing times and failures

