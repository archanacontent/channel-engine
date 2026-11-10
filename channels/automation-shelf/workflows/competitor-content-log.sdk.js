// Competitor Content Log: logs every new post from a blog's RSS feed to a Google Sheet.
// Validated with n8n validate_workflow on 2026-11-10: valid, 2 nodes.
import { workflow, node, trigger, newCredential, expr } from '@n8n/workflow-sdk';

const newPost = trigger({
  type: 'n8n-nodes-base.rssFeedReadTrigger',
  version: 1,
  config: {
    name: 'New Competitor Post',
    parameters: {
      pollTimes: { item: [{ mode: 'everyHour' }] },
      feedUrl: 'https://example.com/blog/rss/'
    }
  }
});

const logPost = node({
  type: 'n8n-nodes-base.googleSheets',
  version: 4.7,
  config: {
    name: 'Log Post to Sheet',
    parameters: {
      resource: 'sheet',
      operation: 'append',
      documentId: { __rl: true, mode: 'list', value: '', cachedResultName: 'Competitor Content Log' },
      sheetName: { __rl: true, mode: 'name', value: 'Posts' },
      columns: {
        mappingMode: 'defineBelow',
        value: {
          Date: expr('{{ $json.isoDate }}'),
          Title: expr('{{ $json.title }}'),
          Link: expr('{{ $json.link }}'),
          Summary: expr('{{ $json.contentSnippet }}')
        },
        schema: [
          { id: 'Date', displayName: 'Date', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'Title', displayName: 'Title', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'Link', displayName: 'Link', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'Summary', displayName: 'Summary', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true }
        ]
      },
      options: {}
    },
    credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') }
  }
});

export default workflow('competitor-content-log', 'Competitor Content Log')
  .add(newPost)
  .to(logPost);
