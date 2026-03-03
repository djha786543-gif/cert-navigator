import { z } from 'zod';

export const ArtifactSchema = z.object({
  focusDomains: z.array(z.string()).min(1, "Select at least one domain"),
  artifactType: z.enum(['Audit Lab', 'Controls Quick-Ref', 'Audit Simulation']),
  userProfile: z.object({
    certifications: z.array(z.string()),
    experienceLevel: z.string()
  })
});
