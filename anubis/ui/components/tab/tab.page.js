import { AutoloadPage } from '../../misc/PageLoader';
import Tab from './Tab';

const tabPage = new AutoloadPage(() => {
    Tab.initAll();
});

export default tabPage;
