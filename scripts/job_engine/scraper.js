const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Configuration
const SEARCH_QUERIES = [
  'IT Audit Manager',
  'Senior IT Auditor',
  'GRC Manager',
  'AI Governance Risk'
];
const LOCATION = 'Remote'; // or 'Los Angeles, CA'

const delay = (time) => new Promise((resolve) => setTimeout(resolve, time));

async function scrapeIndeed(query, location) {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  // Set a realistic user agent
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36');
  
  const encodedQuery = encodeURIComponent(query);
  const encodedLocation = encodeURIComponent(location);
  const url = `https://www.indeed.com/jobs?q=${encodedQuery}&l=${encodedLocation}`;
  
  console.log(`Scraping URL: ${url}`);
  
  try {
    await page.goto(url, { waitUntil: 'networkidle2' });
    
    // Check for Cloudflare/Captcha (Optional logic to handle blocks)
    // For a real production app we'd need proxy rotation or an API like proxycrawl
    
    const jobs = await page.evaluate(() => {
      const jobCards = document.querySelectorAll('td.resultContent');
      const results = [];
      
      jobCards.forEach(card => {
        const titleEl = card.querySelector('h2.jobTitle span[title]');
        const companyEl = card.querySelector('[data-testid="company-name"]');
        const locationEl = card.querySelector('[data-testid="text-location"]');
        const baseHrefEl = card.querySelector('h2.jobTitle a');
        const metadataEl = card.querySelector('div.jobMetaDataGroup');
        const snippetEl = card.querySelector('div.job-snippet'); // Usually not in resultContent directly but close
        
        if (titleEl && companyEl) {
          const title = titleEl.getAttribute('title');
          const company = companyEl.textContent.trim();
          const loc = locationEl ? locationEl.textContent.trim() : '';
          const baseUrl = window.location.origin;
          const relativeUrl = baseHrefEl ? baseHrefEl.getAttribute('href') : '';
          const redirectUrl = relativeUrl ? baseUrl + relativeUrl : '';
          const metaText = metadataEl ? metadataEl.textContent.trim() : '';
          
          results.push({
            title,
            company: { display_name: company },
            location: { display_name: loc },
            description: metaText + " (Snippet not fully loaded from list view)", // We fetch the snippet/description if needed
            redirect_url: redirectUrl,
            source: 'indeed_subagent'
          });
        }
      });
      return results;
    });
    
    // Add IDs and timestamp
    const now = new Date().toISOString();
    jobs.forEach(job => {
        const hash = crypto.createHash('sha256');
        hash.update(job.title + job.company.display_name + job.source);
        job.id = hash.digest('hex');
        job.created = now;
        
        // Rough salary extraction if it exists in the metadata text
        // Looks for things like "$90,000 - $120,000 a year"
        const salaryMatch = job.description.match(/\$([0-9,]+)/g);
        if (salaryMatch && salaryMatch.length >= 2) {
            job.salary_min = parseFloat(salaryMatch[0].replace(/[$,]/g, ''));
            job.salary_max = parseFloat(salaryMatch[1].replace(/[$,]/g, ''));
        } else if (salaryMatch && salaryMatch.length === 1) {
            job.salary_min = parseFloat(salaryMatch[0].replace(/[$,]/g, ''));
            job.salary_max = job.salary_min;
        }
    });
    
    console.log(`Found ${jobs.length} jobs for ${query}`);
    await browser.close();
    return jobs;
    
  } catch (error) {
    console.error(`Error scraping ${query}:`, error);
    await browser.close();
    return [];
  }
}

async function run() {
  const allJobs = [];
  
  for (const query of SEARCH_QUERIES) {
    const jobs = await scrapeIndeed(query, LOCATION);
    allJobs.push(...jobs);
    // Be polite between queries
    await delay(3000);
  }
  
  const outputPath = path.join(__dirname, 'mock_scraped_data.json');
  fs.writeFileSync(outputPath, JSON.stringify(allJobs, null, 2));
  console.log(`Saved ${allJobs.length} jobs to ${outputPath}`);
}

run();
