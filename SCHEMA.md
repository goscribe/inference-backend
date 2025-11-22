# TypeScript/Prisma Schema Reference

This document shows the expected schema for workspace data that `get_workspace_context` fetches.

## FileAsset Schema

```typescript
// Prisma Schema
model FileAsset {
  id                String    @id @default(cuid())
  userId            String
  workspaceId       String?   // Optional, can be null
  fileName          String
  fileType          String    // 'pdf', 'image', 'document', etc.
  storageUrl        String    // Supabase Storage URL (signed or public)
  storagePath       String    // Path in Supabase Storage
  
  // Pre-processed content (from process_file endpoint)
  processedContent      String?  // comprehensiveDescription from process_file
  textContent           String?  // Raw extracted text from PDFs
  imageDescriptions     Json?    // Array of page descriptions
  processingStatus      String   @default("pending") // 'pending', 'processing', 'completed', 'failed'
  processingError       String?  // Error message if processing failed
  processedAt           DateTime?
  
  // Metadata
  pageCount             Int?
  fileSize              Int      // Size in bytes
  mimeType              String?
  createdAt             DateTime @default(now())
  updatedAt             DateTime @updatedAt
  
  // Relations
  workspace             Workspace? @relation(fields: [workspaceId], references: [id])
  
  @@index([userId])
  @@index([workspaceId])
  @@index([processingStatus])
}
```

### FileAsset TypeScript Type

```typescript
type FileAsset = {
  id: string;
  userId: string;
  workspaceId: string | null;
  fileName: string;
  fileType: 'pdf' | 'image' | 'document' | string;
  storageUrl: string;
  storagePath: string;
  
  // Processed content
  processedContent: string | null;
  textContent: string | null;
  imageDescriptions: ImageDescription[] | null;
  processingStatus: 'pending' | 'processing' | 'completed' | 'failed';
  processingError: string | null;
  processedAt: Date | null;
  
  // Metadata
  pageCount: number | null;
  fileSize: number;
  mimeType: string | null;
  createdAt: Date;
  updatedAt: Date;
};

type ImageDescription = {
  page: number;
  description: string;
  hasVisualContent: boolean;
};
```

## Flashcard Schema

```typescript
// Prisma Schema
model Flashcard {
  id            String    @id @default(cuid())
  userId        String
  workspaceId   String
  term          String    // Question/Term
  definition    String    // Answer/Definition
  difficulty    String?   // 'easy', 'medium', 'hard'
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  
  // Relations
  workspace     Workspace @relation(fields: [workspaceId], references: [id])
  
  @@index([userId])
  @@index([workspaceId])
}
```

### Flashcard TypeScript Type

```typescript
type Flashcard = {
  id: string;
  userId: string;
  workspaceId: string;
  term: string;
  definition: string;
  difficulty: 'easy' | 'medium' | 'hard' | null;
  createdAt: Date;
  updatedAt: Date;
};
```

## Workspace Schema (Reference)

```typescript
// Prisma Schema
model Workspace {
  id            String       @id @default(cuid())
  userId        String
  name          String?
  createdAt     DateTime     @default(now())
  updatedAt     DateTime     @updatedAt
  
  // Relations
  fileAssets    FileAsset[]
  flashcards    Flashcard[]
  worksheets    Worksheet[]
  
  @@index([userId])
}
```

## API Response Types

### FileAsset API Response

```typescript
// GET /api/fileAssets?workspaceId=xxx&userId=xxx
type FileAssetsResponse = FileAsset[];

// Expected format for get_workspace_context
type FileAssetForContext = {
  fileName: string;
  fileType: string;
  processedContent: string | null;
  textContent: string | null;
  imageDescriptions: ImageDescription[] | null;
  pageCount: number | null;
  processingStatus: string;
  processingError?: string;
};
```

### Flashcard API Response

```typescript
// GET /api/flashcards?workspaceId=xxx&userId=xxx
type FlashcardsResponse = Flashcard[];

// Expected format for get_workspace_context
type FlashcardForContext = {
  term: string;
  definition: string;
  difficulty?: string;
};
```

## Example API Endpoints (tRPC)

```typescript
// tRPC Router Example
export const fileAssetRouter = router({
  getByWorkspace: publicProcedure
    .input(z.object({
      workspaceId: z.string(),
      userId: z.string(),
    }))
    .query(async ({ ctx, input }) => {
      return await ctx.prisma.fileAsset.findMany({
        where: {
          workspaceId: input.workspaceId,
          userId: input.userId,
        },
        orderBy: {
          createdAt: 'desc',
        },
      });
    }),
});

export const flashcardRouter = router({
  getByWorkspace: publicProcedure
    .input(z.object({
      workspaceId: z.string(),
      userId: z.string(),
    }))
    .query(async ({ ctx, input }) => {
      return await ctx.prisma.flashcard.findMany({
        where: {
          workspaceId: input.workspaceId,
          userId: input.userId,
        },
        orderBy: {
          createdAt: 'desc',
        },
      });
    }),
});
```

## Example Usage in Python

```python
from app.utils.workspace_context import get_workspace_context_as_message

# Get context as message (ready to prepend to LLM messages)
context_message = get_workspace_context_as_message(
    workspace_id="workspace_123",
    user_id="user_456",
    include_file_assets=True,
    include_flashcards=True
)

# Prepend to messages before calling LLM
messages = []
if context_message:
    messages.append(context_message)

# Add your prompt
messages.append({
    "role": "user",
    "content": "Generate a podcast about the uploaded files..."
})

# Call LLM
resp = LLM_inference(messages=messages)
```

