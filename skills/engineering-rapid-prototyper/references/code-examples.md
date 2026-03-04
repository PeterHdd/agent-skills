# Code Examples

## Rapid UI with react-hook-form + shadcn/ui
```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { toast } from '@/components/ui/use-toast';

const feedbackSchema = z.object({
  content: z.string().min(10, 'Feedback must be at least 10 characters'),
  rating: z.number().min(1).max(5),
  email: z.string().email('Invalid email address'),
});

type FeedbackValues = z.infer<typeof feedbackSchema>;

export function FeedbackForm() {
  const form = useForm<FeedbackValues>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: { content: '', rating: 5, email: '' },
  });

  async function onSubmit(values: FeedbackValues) {
    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      if (!response.ok) throw new Error('Failed to submit feedback');
      toast({ title: 'Feedback submitted successfully!' });
      form.reset();
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to submit feedback. Please try again.',
        variant: 'destructive',
      });
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <Input placeholder="Your email" {...form.register('email')} className="w-full" />
        {form.formState.errors.email && (
          <p className="text-red-500 text-sm mt-1">{form.formState.errors.email.message}</p>
        )}
      </div>
      <div>
        <Textarea
          placeholder="Share your feedback..."
          {...form.register('content')}
          className="w-full min-h-[100px]"
        />
        {form.formState.errors.content && (
          <p className="text-red-500 text-sm mt-1">{form.formState.errors.content.message}</p>
        )}
      </div>
      <div className="flex items-center space-x-2">
        <label htmlFor="rating">Rating:</label>
        <select
          {...form.register('rating', { valueAsNumber: true })}
          className="border rounded px-2 py-1"
        >
          {[1, 2, 3, 4, 5].map(num => (
            <option key={num} value={num}>{num} star{num > 1 ? 's' : ''}</option>
          ))}
        </select>
      </div>
      <Button type="submit" disabled={form.formState.isSubmitting} className="w-full">
        {form.formState.isSubmitting ? 'Submitting...' : 'Submit Feedback'}
      </Button>
    </form>
  );
}
```

## Analytics and A/B Testing
```typescript
import { useEffect, useState, useMemo } from 'react';

// Lightweight analytics helper
export function trackEvent(eventName: string, properties?: Record<string, any>) {
  if (typeof window !== 'undefined') {
    window.gtag?.('event', eventName, properties);
    fetch('/api/analytics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: eventName,
        properties,
        timestamp: Date.now(),
        url: window.location.href,
      }),
    }).catch(() => {}); // Fire-and-forget
  }
}

// A/B testing hook — variants array is memoized to prevent infinite re-renders
export function useABTest(testName: string, variants: string[]) {
  // Memoize variants so the useEffect dependency is referentially stable
  const stableVariants = useMemo(() => variants, [JSON.stringify(variants)]);
  const [variant, setVariant] = useState<string>('');

  useEffect(() => {
    let userId = localStorage.getItem('user_id');
    if (!userId) {
      userId = crypto.randomUUID();
      localStorage.setItem('user_id', userId);
    }

    const hash = [...userId].reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0);
      return a & a;
    }, 0);

    const variantIndex = Math.abs(hash) % stableVariants.length;
    const assignedVariant = stableVariants[variantIndex];
    setVariant(assignedVariant);

    trackEvent('ab_test_assignment', {
      test_name: testName,
      variant: assignedVariant,
      user_id: userId,
    });
  }, [testName, stableVariants]);

  return variant;
}

// Usage — pass literal array; useMemo inside the hook prevents re-render loop
export function LandingPageHero() {
  const heroVariant = useABTest('hero_cta', ['Sign Up Free', 'Start Your Trial']);

  if (!heroVariant) return <div>Loading...</div>;

  return (
    <section className="text-center py-20">
      <h1 className="text-4xl font-bold mb-6">Revolutionary Prototype App</h1>
      <p className="text-xl mb-8">Validate your ideas faster than ever before</p>
      <button
        onClick={() => trackEvent('hero_cta_click', { variant: heroVariant })}
        className="bg-blue-600 text-white px-8 py-3 rounded-lg text-lg hover:bg-blue-700"
      >
        {heroVariant}
      </button>
    </section>
  );
}
```
