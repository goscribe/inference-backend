# Podcast Generation - Frontend Implementation Guide

## Overview

Three main API calls:
1. **Generate Structure** - Get the podcast script with dialogue
2. **Generate Audio** - Convert each segment to audio (handles multi-speaker dialogue automatically)
3. **Regenerate Segment** - Redo a specific segment if you're not happy with it

---

## Step 1: Generate Structure

### Request

```typescript
const structureFormData = new FormData();
structureFormData.append("command", "generate_podcast_structure");
structureFormData.append("user", userId);           // Your user ID
structureFormData.append("session", sessionId);     // Your session ID
structureFormData.append("title", "Introduction to Machine Learning");
structureFormData.append("description", "A beginner's guide to ML concepts");
structureFormData.append("prompt", "Focus on practical examples");  // Optional
structureFormData.append("speakers", JSON.stringify([
  { id: "pNInz6obpgDQGcFmaJgB", role: "host" },
  { id: "XB0fDUnXU5powFXDhCwa", role: "guest" }
]));

const response = await fetch('http://your-python-backend/upload', {
  method: 'POST',
  body: structureFormData
});

const data = await response.json();
```

### Response

```json
{
  "success": true,
  "structure": {
    "episodeTitle": "Introduction to Machine Learning: A Beginner's Guide",
    "totalEstimatedDuration": "15 minutes",
    "segments": [
      {
        "title": "Welcome & Introduction",
        "content": "HOST: Welcome to today's episode!\nGUEST: Thanks for having me!\nHOST: Let's dive into machine learning.\nGUEST: Great! Let's start with the basics...",
        "speaker": "dialogue",
        "voiceId": "pNInz6obpgDQGcFmaJgB",
        "keyPoints": ["Introduction", "What to expect"],
        "estimatedDuration": "3 minutes",
        "order": 1
      },
      {
        "title": "What is Machine Learning?",
        "content": "Machine learning is a subset of artificial intelligence...",
        "speaker": "host",
        "voiceId": "pNInz6obpgDQGcFmaJgB",
        "keyPoints": ["Definition", "Key concepts"],
        "estimatedDuration": "4 minutes",
        "order": 2
      }
    ]
  }
}
```

---

## Step 2: Generate Audio for Each Segment

Loop through segments and generate audio. The backend automatically:
- Detects dialogue (HOST:, GUEST:, etc.)
- Generates separate audio for each speaker
- Concatenates them into ONE file
- Uploads to Supabase
- Returns the object key

### Request

```typescript
const audioFormData = new FormData();
audioFormData.append("command", "generate_podcast_audio_from_text");
audioFormData.append("user", userId);
audioFormData.append("session", sessionId);
audioFormData.append("podcast_id", episodeId);        // Your episode ID
audioFormData.append("segment_index", "0");           // Current segment index
audioFormData.append("text", segment.content);        // Full text (with dialogue markers)
audioFormData.append("speakers", JSON.stringify([
  { id: "pNInz6obpgDQGcFmaJgB", role: "host" },
  { id: "XB0fDUnXU5powFXDhCwa", role: "guest" }
]));

// For monologue only (optional):
audioFormData.append("voice_id", "pNInz6obpgDQGcFmaJgB");

const response = await fetch('http://your-python-backend/upload', {
  method: 'POST',
  body: audioFormData
});

const data = await response.json();
```

### Response

**Dialogue Segment:**
```json
{
  "success": true,
  "segmentIndex": 0,
  "objectKey": "user123/session456/podcasts/episode_001/segment_0.mp3",
  "duration": 45,
  "type": "dialogue",
  "partCount": 4
}
```

**Monologue Segment:**
```json
{
  "success": true,
  "segmentIndex": 1,
  "objectKey": "user123/session456/podcasts/episode_001/segment_1.mp3",
  "duration": 30,
  "type": "monologue"
}
```

---

## Complete Implementation Example

### Plain JavaScript/TypeScript

```typescript
async function generatePodcast({
  title,
  description,
  speakers,
  userId,
  sessionId
}: PodcastInput) {
  
  const API_URL = 'http://your-python-backend/upload';
  const episodeId = `episode_${Date.now()}`; // Or use uuidv4()
  
  try {
    // ========================================
    // STEP 1: GENERATE STRUCTURE
    // ========================================
    console.log('📝 Generating podcast structure...');
    
    const structureFormData = new FormData();
    structureFormData.append("command", "generate_podcast_structure");
    structureFormData.append("user", userId);
    structureFormData.append("session", sessionId);
    structureFormData.append("title", title);
    structureFormData.append("description", description);
    structureFormData.append("speakers", JSON.stringify(speakers));
    
    const structureRes = await fetch(API_URL, {
      method: 'POST',
      body: structureFormData
    });
    
    if (!structureRes.ok) {
      throw new Error('Failed to generate structure');
    }
    
    const { structure } = await structureRes.json();
    console.log(`✅ Got ${structure.segments.length} segments`);
    
    // Save structure to your database
    const episode = await db.podcastEpisode.create({
      data: {
        title: structure.episodeTitle,
        description: description,
        segmentCount: structure.segments.length,
        generating: true
      }
    });
    
    // ========================================
    // STEP 2: GENERATE AUDIO FOR EACH SEGMENT
    // ========================================
    console.log('🎵 Generating audio...');
    
    const audioFiles = [];
    
    for (let i = 0; i < structure.segments.length; i++) {
      const segment = structure.segments[i];
      
      console.log(`Generating ${i + 1}/${structure.segments.length}: ${segment.title}`);
      
      // Show progress to user
      updateProgress({
        current: i + 1,
        total: structure.segments.length,
        segmentTitle: segment.title
      });
      
      const audioFormData = new FormData();
      audioFormData.append("command", "generate_podcast_audio_from_text");
      audioFormData.append("user", userId);
      audioFormData.append("session", sessionId);
      audioFormData.append("podcast_id", episodeId);
      audioFormData.append("segment_index", i.toString());
      audioFormData.append("text", segment.content);
      audioFormData.append("speakers", JSON.stringify(speakers));
      
      const audioRes = await fetch(API_URL, {
        method: 'POST',
        body: audioFormData
      });
      
      if (!audioRes.ok) {
        console.error(`Failed to generate segment ${i}`);
        continue; // Skip failed segments
      }
      
      const audioData = await audioRes.json();
      audioFiles.push(audioData);
      
      // Save to database immediately
      await db.podcastSegment.create({
        data: {
          episodeId: episode.id,
          objectKey: audioData.objectKey,
          title: segment.title,
          content: segment.content,
          duration: audioData.duration,
          order: i,
          type: audioData.type
        }
      });
      
      console.log(`✅ Segment ${i + 1} complete`);
    }
    
    // ========================================
    // STEP 3: MARK AS COMPLETE
    // ========================================
    await db.podcastEpisode.update({
      where: { id: episode.id },
      data: {
        generating: false,
        completedAt: new Date()
      }
    });
    
    console.log('🎉 Podcast generation complete!');
    
    return {
      episodeId: episode.id,
      title: structure.episodeTitle,
      segmentCount: audioFiles.length,
      audioFiles
    };
    
  } catch (error) {
    console.error('❌ Error:', error);
    throw error;
  }
}
```

---

## Next.js tRPC Implementation

```typescript
// src/server/api/routers/podcast.ts

import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "~/server/api/trpc";

const speakerSchema = z.object({
  id: z.string(),
  role: z.enum(["host", "guest", "expert"]),
  name: z.string().optional()
});

export const podcastRouter = createTRPCRouter({
  
  generateEpisode: protectedProcedure
    .input(z.object({
      workspaceId: z.string(),
      title: z.string(),
      description: z.string().optional(),
      speakers: z.array(speakerSchema).min(1)
    }))
    .mutation(async ({ ctx, input }) => {
      
      const PYTHON_API = process.env.PYTHON_BACKEND_URL || 'http://localhost:61016/upload';
      
      // 1. Generate structure
      const structureFormData = new FormData();
      structureFormData.append("command", "generate_podcast_structure");
      structureFormData.append("user", ctx.session.user.id);
      structureFormData.append("session", input.workspaceId);
      structureFormData.append("title", input.title);
      structureFormData.append("description", input.description || "");
      structureFormData.append("speakers", JSON.stringify(input.speakers));
      
      const structureRes = await fetch(PYTHON_API, {
        method: 'POST',
        body: structureFormData
      });
      
      if (!structureRes.ok) {
        throw new Error('Failed to generate structure');
      }
      
      const { structure } = await structureRes.json();
      
      // Create episode in database
      const episode = await ctx.db.podcastEpisode.create({
        data: {
          workspaceId: input.workspaceId,
          title: structure.episodeTitle,
          description: input.description,
          segmentCount: structure.segments.length,
          generating: true,
          createdById: ctx.session.user.id
        }
      });
      
      // 2. Generate audio for each segment
      for (let i = 0; i < structure.segments.length; i++) {
        const segment = structure.segments[i];
        
        // Emit progress via Pusher/WebSocket
        await ctx.pusher.trigger(`workspace-${input.workspaceId}`, 'podcast-progress', {
          current: i + 1,
          total: structure.segments.length,
          segmentTitle: segment.title
        });
        
        const audioFormData = new FormData();
        audioFormData.append("command", "generate_podcast_audio_from_text");
        audioFormData.append("user", ctx.session.user.id);
        audioFormData.append("session", input.workspaceId);
        audioFormData.append("podcast_id", episode.id);
        audioFormData.append("segment_index", i.toString());
        audioFormData.append("text", segment.content);
        audioFormData.append("speakers", JSON.stringify(input.speakers));
        
        const audioRes = await fetch(PYTHON_API, {
          method: 'POST',
          body: audioFormData
        });
        
        if (!audioRes.ok) {
          console.error(`Failed to generate segment ${i}`);
          continue;
        }
        
        const audioData = await audioRes.json();
        
        // Save segment
        await ctx.db.podcastSegment.create({
          data: {
            episodeId: episode.id,
            objectKey: audioData.objectKey,
            title: segment.title,
            content: segment.content,
            duration: audioData.duration,
            order: i,
            segmentType: audioData.type,
            keyPoints: segment.keyPoints
          }
        });
      }
      
      // 3. Mark complete
      await ctx.db.podcastEpisode.update({
        where: { id: episode.id },
        data: {
          generating: false,
          completedAt: new Date()
        }
      });
      
      // Emit completion
      await ctx.pusher.trigger(`workspace-${input.workspaceId}`, 'podcast-complete', {
        episodeId: episode.id
      });
      
      return episode;
    })
});
```

---

## React Component with Progress

```tsx
'use client';

import { useState } from 'react';
import { api } from '~/trpc/react';

export function PodcastGenerator() {
  const [progress, setProgress] = useState({ current: 0, total: 0, title: '' });
  
  const generateMutation = api.podcast.generateEpisode.useMutation();
  
  // Listen for progress events (if using Pusher)
  useEffect(() => {
    const channel = pusher.subscribe(`workspace-${workspaceId}`);
    
    channel.bind('podcast-progress', (data: any) => {
      setProgress({
        current: data.current,
        total: data.total,
        title: data.segmentTitle
      });
    });
    
    return () => {
      channel.unbind_all();
      channel.unsubscribe();
    };
  }, [workspaceId]);
  
  const handleGenerate = async () => {
    try {
      await generateMutation.mutateAsync({
        workspaceId: workspaceId,
        title: 'ML Basics',
        description: 'Introduction to Machine Learning',
        speakers: [
          { id: 'pNInz6obpgDQGcFmaJgB', role: 'host' },
          { id: 'XB0fDUnXU5powFXDhCwa', role: 'guest' }
        ]
      });
      
      toast.success('Podcast generated!');
    } catch (error) {
      toast.error('Failed to generate podcast');
    }
  };
  
  return (
    <div>
      <button onClick={handleGenerate} disabled={generateMutation.isPending}>
        Generate Podcast
      </button>
      
      {generateMutation.isPending && (
        <div className="progress">
          <div className="progress-bar">
            <div style={{ width: `${(progress.current / progress.total) * 100}%` }} />
          </div>
          <p>
            Generating segment {progress.current}/{progress.total}: {progress.title}
          </p>
        </div>
      )}
    </div>
  );
}
```

---

## Key Points

✅ **Two API calls total**: One for structure, one per segment for audio  
✅ **Automatic dialogue handling**: Backend splits and joins automatically  
✅ **One file per segment**: Regardless of dialogue or monologue  
✅ **Progress tracking**: Update UI as each segment completes  
✅ **Error resilient**: Can retry individual segments  
✅ **Supabase storage**: All audio uploaded automatically  

## Speaker Configuration

### 2 Speakers (Host + Guest)
```typescript
const speakers = [
  { id: "voice_id_1", role: "host" },
  { id: "voice_id_2", role: "guest" }
];
```

### 3+ Speakers
```typescript
const speakers = [
  { id: "voice_id_1", role: "host" },
  { id: "voice_id_2", role: "guest" },
  { id: "voice_id_3", role: "expert" }
];
```

The LLM will automatically create dialogue between all speakers!

---

## Error Handling

```typescript
try {
  const audioData = await generateAudio(segment);
  // Success
} catch (error) {
  if (error.message.includes('rate limit')) {
    // Wait and retry
    await sleep(5000);
    return generateAudio(segment);
  } else {
    // Log and skip
    console.error(`Segment ${i} failed:`, error);
    // Continue with next segment
  }
}
```

---

## Playing Audio in Frontend

Once you have the `objectKey`, get the public URL from Supabase:

```typescript
const { data } = supabase
  .storage
  .from('media')
  .getPublicUrl(audioData.objectKey);

// Use in audio player
<audio src={data.publicUrl} controls />
```

---

## Step 3 (Optional): Regenerate a Segment

If you're not happy with a specific segment, regenerate just that one without redoing the whole podcast.

### Request

```typescript
const formData = new FormData();
formData.append("command", "regenerate_podcast_segment");
formData.append("user", userId);
formData.append("session", sessionId);
formData.append("structure", JSON.stringify(fullStructure));  // The complete structure
formData.append("segment_index", "2");  // Which segment to regenerate (0-based)
formData.append("notes", "Make it shorter and add more examples");  // Optional guidance

const response = await fetch('http://your-python-backend/upload', {
  method: 'POST',
  body: formData
});

const data = await response.json();
```

### Response

```json
{
  "success": true,
  "segmentIndex": 2,
  "newSegment": {
    "title": "Types of Machine Learning",
    "content": "RACHEL: Let's discuss the different types...\nJOSH: Sure! There are three main categories...",
    "speaker": "dialogue",
    "voiceId": "pNInz6obpgDQGcFmaJgB",
    "keyPoints": ["Supervised learning", "Unsupervised learning"],
    "estimatedDuration": "4 minutes",
    "order": 3
  }
}
```

### Usage Example

```typescript
// User clicks "Regenerate" on segment 2
async function regenerateSegment(segmentIndex: number, notes?: string) {
  const formData = new FormData();
  formData.append("command", "regenerate_podcast_segment");
  formData.append("user", userId);
  formData.append("session", sessionId);
  formData.append("structure", JSON.stringify(currentStructure));
  formData.append("segment_index", segmentIndex.toString());
  if (notes) {
    formData.append("notes", notes);
  }
  
  const res = await fetch(API_URL, { method: 'POST', body: formData });
  const { newSegment } = await res.json();
  
  // Update your structure
  currentStructure.segments[segmentIndex] = newSegment;
  
  // Now generate audio for the new segment
  const audioFormData = new FormData();
  audioFormData.append("command", "generate_podcast_audio_from_text");
  audioFormData.append("user", userId);
  audioFormData.append("session", sessionId);
  audioFormData.append("podcast_id", episodeId);
  audioFormData.append("segment_index", segmentIndex.toString());
  audioFormData.append("text", newSegment.content);
  audioFormData.append("speakers", JSON.stringify(speakers));
  
  const audioRes = await fetch(API_URL, { method: 'POST', body: audioFormData });
  const audioData = await audioRes.json();
  
  // Update database with new audio
  await db.podcastSegment.update({
    where: { 
      episodeId_order: { episodeId, order: segmentIndex }
    },
    data: {
      objectKey: audioData.objectKey,
      content: newSegment.content,
      duration: audioData.duration
    }
  });
  
  toast.success("Segment regenerated!");
}
```

### UI Example

```tsx
<div className="segment">
  <h3>{segment.title}</h3>
  <p>{segment.content.substring(0, 100)}...</p>
  <button onClick={() => regenerateSegment(index)}>
    🔄 Regenerate
  </button>
  <button onClick={() => {
    const notes = prompt("What should we change?");
    if (notes) regenerateSegment(index, notes);
  }}>
    ✏️ Regenerate with notes
  </button>
</div>
```

### Common Regeneration Notes

- "Make it shorter"
- "Add more examples"
- "Make it more conversational"
- "Simplify the technical terms"
- "Add more humor"
- "Focus more on practical applications"

---

That's it! Three simple API calls for complete control over your multi-speaker podcast! 🎙️

