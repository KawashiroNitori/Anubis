import { AutoloadPage } from '../../misc/PageLoader';
import hljs from '../highlighter/hljs';

function runHighlight($container) {
    hljs.highlightBlocks($container);
}

const highlighterPage = new AutoloadPage(() => {
    runHighlight($('body'));
    $(document).on('ContentNew', e => runHighlight($(e.target)));
});

export default highlighterPage;
