import test from 'node:test';
import assert from 'node:assert/strict';
import {quotationMarkdown,readingWords,readingFeedbackIsCurrent} from '../dist/reading.js';
import {plannerRoute} from '../dist/planner.js';
import {navigationFor} from '../dist/navigation.js';

test('quote notebook preserves exact wording and distinguishes interpretation',()=>{
 const value=quotationMarkdown({text:'Some results—\nnot all.',page:'42',context:'A small sample',interpretation:'My inference',checked:false});
 assert.ok(value.includes('> Some results—\n> not all.'));
 assert.ok(value.includes('**My interpretation / limits:** My inference'));
 assert.ok(value.includes('**Checked against source by me:** Not yet'));
 assert.throws(()=>quotationMarkdown({text:'Words',page:'',context:'',interpretation:''}));
});
test('an edited summary is visibly different from the reviewed snapshot',()=>{
 assert.equal(readingFeedbackIsCurrent({reviewed_text:'My summary'},'My summary\n'),true);
 assert.equal(readingFeedbackIsCurrent({reviewed_text:'My summary'},'My revised summary'),false);
 assert.equal(readingWords('One  two\nthree'),3);
});
test('reading has its own navigation and planner return routes stay local',()=>{
 assert.equal(navigationFor('reading').group,'reading');
 assert.equal(plannerRoute('#papers/abc?card=def'),'#papers/abc?card=def');
 assert.equal(plannerRoute('#reading/abc'),'#reading/abc');
 assert.equal(plannerRoute('https://other.test/'),'');
 assert.equal(plannerRoute('#reading/abc" onclick="bad'),'');
});
